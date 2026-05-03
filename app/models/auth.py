from pydantic import BaseModel, EmailStr

class RegisterRequest(BaseModel):
    dog_name: str
    email: EmailStr
    is_neutered: bool
    password: str
    password_vertify: str
    size: str
    user_name: str
    vaccination_count: int


class LoginRequest(BaseModel):
    user_name: str
    password: str