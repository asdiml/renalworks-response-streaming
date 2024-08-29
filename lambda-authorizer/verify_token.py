import requests, os
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from jwk_to_pem import jwk_to_pem

region = os.environ['AWS_REGION']
user_pool_id = os.environ['TOALLOW_COGNITO_USER_POOL_ID']

jwksUrl = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json"

def get_pubkeys_from_url(jwksUrl):
    
    print(f"Retrieving public keys from {jwksUrl}")

    response = requests.get(jwksUrl)

    if response.status_code != 200:
      raise Exception("Unable to retrieve public keys from {jwksUrl}")
    
    pubkeys_jwk_json = response.json()
    pubkeys_pem = {}

    for pubkey_jwk in pubkeys_jwk_json['keys']:
      kid = pubkey_jwk['kid']
      pubkeys_pem[kid] = {
         "pubkey": jwk_to_pem(pubkey_jwk),
         "alg": pubkey_jwk['alg']
      }
    
    return pubkeys_pem

def verify_token(token):

    kid = jwt.get_unverified_header(token).get('kid')
    if not kid:
        print('kid field required in the JWT header')

    pubkeys = get_pubkeys_from_url(jwksUrl)
    if not pubkeys.get(kid):
        print('Unauthenticated. User not in the authorized user pool')

    try:
        claims = jwt.decode(token, pubkeys[kid]['pubkey'], algorithms=[pubkeys[kid]['alg']])
        return claims

    except Exception as e: 
        if isinstance(e, ExpiredSignatureError):
            print("Signature expired. Please obtain a new auth token. ")
        elif isinstance(e, InvalidTokenError):
            print("Invalid signature")
        else:
            print(f"Exception raised: {e}")
        return None