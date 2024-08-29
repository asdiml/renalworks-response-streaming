import os
from generate_policy import generateAllowPolicy, generateDenyPolicy
from verify_token import verify_token

COGNITO_AUTHORIZER_IDENTITY_SOURCE_HEADER_NAME = os.environ['COGNITO_AUTHORIZER_IDENTITY_SOURCE_HEADER_NAME']

def wrapper_deny_access(event_arn):
    def deny_access(msg):
        return generateDenyPolicy('unauthorized', event_arn, {'msg': msg})
    return deny_access
    

def lambda_handler(event, context):

    # Log the event
    print(f"Event: {event}")

    deny_access = wrapper_deny_access(event['methodArn'])

    # Lambda authorizer will not allow requests without the identity source specified in the authorizer, so we do not need to check if these fields exist
    identity_src_header = event["headers"][COGNITO_AUTHORIZER_IDENTITY_SOURCE_HEADER_NAME]
    if identity_src_header[:7] != 'Bearer ':
        return deny_access('Bearer prefix missing')
    if not identity_src_header[7:]:
        return deny_access('No token provided')
    
    claims = verify_token(identity_src_header[7:])
    if not claims:
        return deny_access('Invalid token')

    # Log the validated claims
    print(f"Claims: {claims}")

    # Can change the principal-id field to another category e.g. genai-basic-user
    policy = generateAllowPolicy('genai-pro-user', event['methodArn'], claims)
    print(f"Policy: {policy}")

    return policy