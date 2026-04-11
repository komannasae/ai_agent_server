from fastapi import APIRouter
from Db import save_trip, get_trips_by_user
from model import TripRequest
from agent.travel_agent import recommend_trip_agent
import uuid

router = APIRouter()

@router.post("/create")
def create_trip(data: TripRequest):
    trip_id = str(uuid.uuid4())
    save_trip(
        trip_id=trip_id,
        user_id=data.user_id,
        title=data.title,
        destination=data.destination,
        start_date=data.start_date,
        end_date=data.end_date
    )
    return {"error": False, "trip_id": trip_id}

@router.get("/list/{user_id}")
def get_trips(user_id: str):
    trips = get_trips_by_user(user_id)
    return {"error": False, "trips": trips}

@router.post("/recommend")
async def recommend_trip(data: dict):
    result = await recommend_trip_agent(
        destination=data.get("destination"),
        dog_size=data.get("dog_size"),
        start_date=data.get("start_date"),
        end_date=data.get("end_date"),
    )
    return result