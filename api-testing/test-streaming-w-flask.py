import json
from typing import Iterator, Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage
from langchain_aws import ChatBedrock
from langchain.callbacks.tracers.langchain import wait_for_all_tracers
from langchain_core.runnables import chain

from flask import Flask, Response, jsonify
app = Flask(__name__)

MODEL_ID = 'anthropic.claude-3-5-sonnet-20240620-v1:0'

def get_system_prompt(category: str) -> str:
    prompts = {
        "clinical-note": """
        You are a clinical assistant in RenalGenie. You will be given a series of clinical notes in JSON format. The JSON data will be in the <response> XML tag. 
        Your job is to summarize the clinical note of the patient and provide relevant insights. Provide the summary in point forms. Keep the date time format in simple format for human readibility.
        You are only allowed to provide answer based on the given context, do not answer any question that is out of scope. You may also use a clear table format in your output.
    
        When generating output in point forms, use a clear format, for example:
        1. <b>Item 1</b>: 
                <ul>
                    <li>Explanation A</li>
                    <li>Explanation B</li>
                </ul>

        2. <b>Item 2</b>:
                <ul>
                    <li>Explanation A</li>
                    <li>Explanation B</li>
                </ul>
 
        When generating tables, use the following format: 
        <table>
            <thead>
            <tr>
                <th>Column 1</th>
                <th>Column 2</th>
                <th>Column 3</th>
            </tr>
            </thead>
            <tbody>
            <tr>
                <td>Cell 1</td>
                <td>Cell 2</td>
                <td>Cell 3</td>
            </tr>
            <tr>
                <td>Cell 1</td>
                <td>Cell 2</td>
                <td>Cell 3</td>
            </tr>
            </tbody>
        </table>

        The following are the descriptions of the important parameters in the JSON data: 
        1. id: Unique identifier for each clinical note record.
        2. patient: Patient details, including patient unique identifier, name, and status.
        3. note: Main content of the clinical note, written by doctors or nurses.
        4. type: Type of note, for example, haemodialysis, nephrologist review.
        5. details: Details of the note type.
        6. enteredAt: Date and time when the clinical note was created.
        7. enteredBy: Information about the person who created the clinical note.
        """,
        "lab-result": """
        You are a clinical assistant in RenalGenie. You will be given a series of lab results in JSON format. The JSON data will be in the <response> XML tag. 
        Your job is to summarize the lab results of the patient and provide relevant insights. Provide the summary in point form. Keep the date and time format simple for human readability.
        You are only allowed to provide answer based on the given context, do not answer any question that is out of scope.

        The following are the descriptions of the important parameters in the JSON data: 
        1. categoryCode: Name of the category of the lab tests, each containing a range of lab results. 
        2. ranges: List of the lab tests. 
        3. code: Unique identifier for the lab. 
        4. name: Name of the lab test. 
        5. range: Recommended range of values for the lab result. 
        6. measurement: Unit of measurement for the range. 
        7. resultPackages: Contains all the lab results with actual values.
        8. procedureCode: Unique identifier of the procedure.
        9. procedureName: Name of the procedure. 
        10. labName: Name of the lab. 
        11. completedAt: Date and time of completion.
        12. performedAt: Date and time when the lab started.
        13. resultDate: Date and time when the result was released. 
        14. testSets: Contains the actual result of the lab tests, corresponding to the code. 
        15. value: Actual result of the lab test. 
        16. isAbnormal: Indicates if the value is within the range.

        Insights
        1. Quarterly Nephrologist Review: The patient must be reviewed by a nephrologist every quarter.
        2. Monthly PIC Review: The patient must be reviewed by a PIC every month.
        """
    }
    return prompts.get(category, "")

def get_question(category: str) -> str:
    questions = {
        "clinical-note": """
        Summarize the clinical notes for the patient
        """,
        "lab-result": """
        Summarize the lab results for the patient
        """
    }
    return questions.get(category, "")

def context_limiter(prompt: str, token_limit=30000, average_token_length=4) -> bool:
    # Estimate token count by dividing character count by the average token length
    token_count = len(prompt) / average_token_length
    return token_count <= token_limit

'''
Old parse function that does not allow for streaming
- Kept for reference in case the new `parse` does not allow for invocation without streaming
'''
def parse_no_streaming(ai_message: AIMessage) -> str:
    """Parse the AI message."""
    content = ai_message.content
    
    # Replace single newlines with spaces
    content = content.replace('\n\n', '<newline>')
    content = content.replace('\n', ' ')
    # Replace double spaces (which were originally double newlines) with single newlines
    content = content.replace('<newline>', '\n')

    return content

'''
See https://python.langchain.com/v0.2/docs/how_to/functions/#streaming for instructions on how to add streaming to 
custom functions in chains (in technical terms, chains are called Runnables)
'''
def parse(ai_message: Iterator[AIMessage]) -> Iterator[str]:
    """Parse the AI message."""
    for chunk in ai_message: 
        content = chunk.content
        
        # Replace single newlines with spaces
        content = content.replace('\n\n', '<newline>')
        content = content.replace('\n', ' ')
        # Replace double spaces (which were originally double newlines) with single newlines
        content = content.replace('<newline>', '\n')
        yield content


event = {
  "responseData": [
    "id,note,type,details,fhir_id,id_patient,created_at,modified_at,created_by,modified_by,id_tenant,id_branch,id_dialysis,manually_created,hd_reading_id,lab_order_id,,,,,,,,,,",
    "11989,'pt stable, complete 4 hour hd, no complaint',HD,Post-dialysis,694417,1951,54:09.4,,233,,100,10000,9042,FALSE,,,,,,,,,,,,",
    "11976,'pt stable, no sign of infection, no sign of covid',HD,Pre-dialysis,694027,1951,02:56.5,,233,,100,10000,9042,FALSE,,,,,,,,,,,,",
    "11859,'pt stable and afebrile\nno sign and symptom of infection seen\nno sign and symptom of edema seen\npt on profiling linear, start at 1.15L/hr',HD,Pre-dialysis,690742,1951,19:14.8,,172,,100,10000,8961,FALSE,,,,,,,,,,,,"
  ],
  "category": "clinical-note",
  "userInput": "How is the patient doing?",
  "previousSummary": ""
}

@app.route('/', methods=['GET'])
def main(): 
    # Log the entire event to CloudWatch
    print("Received event: " + json.dumps(event))

    response_data = event.get("responseData", [])
    category = event.get("category")

    formatted_response_data = "".join(response_data)

    if response_data is None or category is None:
        return jsonify({
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "*",
            },
            "body": {
                "errorMessage": "response_data and category are required"
            },
        })

    if not context_limiter(formatted_response_data):
        return jsonify({
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "*",
            },
            "body": {
                "errorMessage": "Context length reached"
            },
        })

    user_input = event.get("userInput")
    previous_summary = event.get("previousSummary")

    PROMPT_TEMPLATE = """\
    {system_prompt}

    <response>
    {response}
    </response>

    Human: {question}

    Assistant: 
    """

    prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    system_prompt = get_system_prompt(category)
    question = get_question(category)

    if previous_summary:
        system_prompt += f"""
        The following is the summary you provided in previous response, modify your answer based on new user question. 
        <previous_summary>
        {previous_summary}
        </previous_summary>
        """

    if user_input:
        question = user_input

    chat = ChatBedrock(
        credentials_profile_name='renalworks-bedrock',
        model_id=MODEL_ID,
        model_kwargs={"temperature": 0.1},
        streaming=True
    )

    chain = prompt | chat | parse

    def generate_response():

        try:
            first_chunk = True
            for chunk in chain.stream(
                {
                    "response": formatted_response_data,
                    "question": question,
                    "system_prompt": system_prompt,
                }
            ):
                if first_chunk:
                    first_chunk = False
                    yield json.dumps({
                        "statusCode": 200,
                        "headers": {
                            "Content-Type": "application/json",
                            "Access-Control-Allow-Headers": "*",
                            "Access-Control-Allow-Origin": "*",
                            "Access-Control-Allow-Methods": "*",
                        },
                    }) + '\n' + chunk
                else: 
                    yield chunk
        
        except Exception as e:
            yield json.dumps({
                "statusCode": 500,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "*",
                },
                "body": {
                    "errorMessage": str(e)
                }
            })
    
    return Response(generate_response(), content_type='application/json')

if __name__ == '__main__':
    app.run(debug=True)