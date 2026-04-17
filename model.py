from pydantic import BaseModel

class LoginRequest(BaseModel):
    user_name: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    name:     str

class DogCreateRequest(BaseModel):
    user_id:           str
    dog_name:          str
    size:              str      # "소형" | "중형" | "대형"
    is_neutered:       bool
    vaccination_count: int

class TripRequest(BaseModel):
    user_id:     str
    title:       str
    destination: str
    start_date:  str
    end_date:    str

class ChatRequest(BaseModel):
    user_id: str
    trip_id: str
    message: str

class FCMRequest(BaseModel):
    user_id: str
    title:   str
    body:    str

class ScheduleWeatherRequest(BaseModel):
    trip_id:       str
    lat:           float
    lng:           float
    schedule_date: str          # "YYYY-MM-DD"