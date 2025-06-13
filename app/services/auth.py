from functools import wraps
from flask import request, jsonify, g
import requests
from jose import jwt, JWTError

def verify_token(token):
    CLERK_ISSUER = "https://right-adder-40.clerk.accounts.dev"
    CLERK_JWKS_URL = f"{CLERK_ISSUER}/.well-known/jwks.json"
    CLERK_AUDIENCE = "https://right-adder-40.clerk.accounts.dev"
    jwks = requests.get(CLERK_JWKS_URL).json()
    try:
        unverified_header = jwt.get_unverified_header(token)
        rsa_key = None
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
        if not rsa_key:
            raise Exception("Public key not found.")
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=CLERK_AUDIENCE,
            issuer=CLERK_ISSUER,
        )
        return payload
    except JWTError as e:
        print("JWT verification failed:", e)
        return None

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", None)
        if not auth_header:
            return jsonify({"error": "Missing Authorization header"}), 401
        try:
            token = auth_header.split(" ")[1]
        except IndexError:
            return jsonify({"error": "Invalid Authorization header format"}), 401
        payload = verify_token(token)
        if not payload:
            return jsonify({"error": "Invalid token"}), 401
        g.user_id = payload["sub"]
        g.user_payload = payload
        return f(*args, **kwargs)
    return decorated 