from fastapi import APIRouter
from Db import save_dog, get_dogs_by_user
from model import DogCreateRequest
import uuid

router = APIRouter()

@router.post("/create")
def create_dog(data: DogCreateRequest):
    dog_id = str(uuid.uuid4())
    save_dog(
        dog_id=dog_id,
        user_id=data.user_id,
        dog_name=data.dog_name,
        size=data.size,
        is_neutered=data.is_neutered,
        vaccination_count=data.vaccination_count
    )
    return {"error": False, "dog_id": dog_id}

@router.get("/list/{user_id}")
def get_dogs(user_id: str):
    dogs = get_dogs_by_user(user_id)
    return {"error": False, "dogs": dogs}