from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import base64

def b64_to_int(b64_string):
    """Convert base64 to integer."""
    return int.from_bytes(base64.urlsafe_b64decode(b64_string + '=='), 'big')

def jwk_to_pem(jwk):
    """Convert a JWK to PEM format."""
    if jwk["kty"] != "RSA":
        raise ValueError("Unsupported key type")
    
    # Convert modulus and exponent from base64 to integers
    modulus = b64_to_int(jwk["n"])
    exponent = b64_to_int(jwk["e"])

    # Build the RSA public key
    public_key = rsa.RSAPublicNumbers(exponent, modulus).public_key()

    # Convert the RSA public key to PEM format
    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    return pem.decode('utf-8')