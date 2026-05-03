import time
import base64
import json

def create_access_token(data: dict):
    """
    ⚠️ 더미 JWT (보안 없음, 테스트용)
    """

    payload = {
        "data": data,
        "iat": int(time.time())
    }

    token = base64.b64encode(
        json.dumps(payload).encode()
    ).decode()

    return token