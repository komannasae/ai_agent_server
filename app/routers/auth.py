from fastapi import APIRouter
from app.models.auth import RegisterRequest, LoginRequest
from app.services.auth_service import register_user, login_user
from app.utils.jwt import create_access_token

router = APIRouter()

@router.post("/register")
def register(req: RegisterRequest):
    user_id, msg = register_user(req)

    if not user_id:
        return {"error": True, "msg": msg}

    return {"error": False, "msg": "회원가입 성공"}


@router.post("/login")
def login(req: LoginRequest):
    user = login_user(req)

    if not user:
        return {
            "error": True,
            "msg": "로그인 실패",
            "token": ""
        }

    token = create_access_token({
        "user_id": user[0],
        "user_name": user[1]
    })

    return {
        "error": False,
        "msg": "",
        "token": token
    }