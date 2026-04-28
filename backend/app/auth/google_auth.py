from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

def verify_google_credential(credential: str, google_client_id: str) -> dict:
    info = id_token.verify_oauth2_token(
        credential,
        google_requests.Request(),
        google_client_id,
    )
    return info