from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from datetime import datetime, timedelta
from dotenv import load_dotenv
from jose import JWTError, jwt
#from passlib.context import CryptContext
import uuid
import os
import bcrypt

from Db import save_user, get_user_by_username, get_user_by_id

load_dotenv()

router = APIRouter()

# ============================
# 설정
# ============================
JWT_SECRET         = os.getenv("JWT_SECRET", "fallback_secret")
JWT_ALGORITHM      = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", 1440))

#pwd_context   = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")



class RegisterRequest(BaseModel):
    username: str
    password: str
    name:     str

class LoginRequest(BaseModel):
    username: str
    password: str



def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

def create_token(user_id: str, username: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user_id, "username": username, "exp": expire},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="토큰 유효하지 않습니다.")

def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    return decode_token(token)


# 회원가입
@router.post("/register")
def register(data: RegisterRequest):
    # 중복 확인
    if get_user_by_username(data.username):
        return {"error": True, "message": "이미 사용 중인 아이디입니다."}

    user_id   = str(uuid.uuid4())
    hashed_pw = hash_password(data.password)
    save_user(user_id, data.name, data.username, hashed_pw)

    token = create_token(user_id, data.username)
    return {
        "error":        False,
        "access_token": token,
        "token_type":   "bearer",
        "user": {"id": user_id, "username": data.username, "name": data.name}
    }


# 로그인
@router.post("/login")
def login(data: LoginRequest):
    user = get_user_by_username(data.username)

    if not user or not verify_password(data.password, user["password"]):
        return {"error": True, "message": "아이디 또는 비밀번호가 올바르지 않습니다."}

    token = create_token(user["id"], data.username)
    return {
        "error":        False,
        "access_token": token,
        "token_type":   "bearer",
        "user": {"id": user["id"], "username": data.username, "name": user["name"]}
    }

token_blacklist: set = set()

# 로그아웃
@router.post("/logout")
def logout():
    return {"error": False, "message": "로그아웃 되었습니다."}

# 내 정보 조회
@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    user = get_user_by_id(current_user["sub"])
    if not user:
        return {"error": True, "message": "사용자를 찾을 수 없습니다."}
    return {"error": False, "user": user}