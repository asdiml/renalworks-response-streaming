#! /usr/bin/env python3.11

import json, boto3

client = boto3.client("bedrock-runtime")

def lambda_handler(event, context):

    llmType = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    messages_API_body = {
        "anthropic_version": "bedrock-2023-05-31", 
        "max_tokens": int(500/0.75),
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "How does heap exploitation work?"
                    }
                ]
            }
        ]
    }

    response_stream = client.invoke_model_with_response_stream(
        body=json.dumps(messages_API_body),
        modelId=llmType,
        accept="application/json",
        contentType="application/json",
    )

    status_code = response_stream["ResponseMetadata"]["HTTPStatusCode"]
    if status_code != 200:
        raise ValueError(f"Error invoking Bedrock API: {status_code}")
    for response in response_stream["body"]:
        json_response = json.loads(response["chunk"]["bytes"])
        if 'delta' in json_response:
            delta_obj = json_response.get('delta', None)
            if delta_obj:
                text = delta_obj.get('text', None)
                print(text)
                if text: 
                    yield text.encode()