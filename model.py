from pydantic import BaseModel

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

class DogCreateRequest(BaseModel):
    user_id: int
    dog_name: str
    size: str               # "소형" | "중형" | "대형"
    is_neutered: bool
    vaccination_count: int

class TripRequest(BaseModel):
    user_id: int
    title: str
    destination: str
    start_date: str
    end_date: str

class ChatRequest(BaseModel):
    user_id: int
    trip_id: int
    message: str

class FCMRequest(BaseModel):
    user_id: int
    title: str
    body: str

class ScheduleWeatherRequest(BaseModel):
    trip_id: int
    lat: float
    lng: float
    schedule_date: str      # "YYYY-MM-DD"

class EvaluateRequest(BaseModel):
    user_id: int
    trip_id: int
    dog_size: str
    destination: str