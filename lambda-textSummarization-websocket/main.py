import os, json
import boto3
from typing import Iterator, Dict, Any, Generator
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage
from langchain_aws import ChatBedrock
from langchain.callbacks.tracers.langchain import wait_for_all_tracers

MODEL_ID = os.environ["MODEL_ID"]

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
See https://python.langchain.com/v0.2/docs/how_to/functions/#streaming for instructions on how to add streaming to 
custom functions in chains (in technical terms, langchain chains are called Runnables)
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

def lambda_handler(event: Dict[str, Any], context: Any) -> Generator[None, Any, None]:

    # Log the entire event to CloudWatch
    print("Received event: " + json.dumps(event))

    event_body = json.loads(event.get("body"))

    response_data = event_body.get("responseData", [])
    category = event_body.get("category")

    formatted_response_data = "".join(response_data)

    if response_data is None or category is None:
        return {
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
        }

    if not context_limiter(formatted_response_data):
        return {
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
        }
    
    user_input = event_body.get("userInput")
    previous_summary = event_body.get("previousSummary")

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
        model_id=MODEL_ID,
        model_kwargs={"temperature": 0.1}
    )

    chain = prompt | chat | parse

    print(chain)

    try:
        connectionId = event['requestContext'].get('connectionId')
        connections_url = os.getenv("CONNECTIONS_URL")
        client = boto3.client("apigatewaymanagementapi", endpoint_url=connections_url, region_name='us-east-1')

        for chunk in chain.stream(
            {
                "response": formatted_response_data,
                "question": question,
                "system_prompt": system_prompt,
            }
        ):
            client.post_to_connection(ConnectionId=connectionId, Data=chunk)
        
        client.delete_connection(ConnectionId=connectionId)
    
    except Exception as e:
        print(str(e))
        return {
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
        }