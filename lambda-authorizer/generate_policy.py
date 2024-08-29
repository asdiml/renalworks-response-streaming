def generatePolicy(principal_id, effect, resource, context):
    return {
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': effect,
                    'Resource': resource,
                }
            ],
        },
        'principalId': principal_id,
        'context': context
    }

def generateAllowPolicy(principal_id, resource, context):
    return generatePolicy(principal_id, 'Allow', resource, context)

def generateDenyPolicy(principal_id, resource, context):
    return generatePolicy(principal_id, 'Deny', resource, context)