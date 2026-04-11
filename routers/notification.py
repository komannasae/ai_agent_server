from fastapi import APIRouter
from model import FCMRequest
from dotenv import load_dotenv
import httpx
import os

load_dotenv()

router = APIRouter()

FCM_SERVER_KEY = os.getenv("FCM_SERVER_KEY", "")

@router.post("/send")
async def send_push(data: FCMRequest):
    fcm_token = "USER_FCM_TOKEN"  # TODO: DB에서 조회
    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://fcm.googleapis.com/fcm/send",
            json={"to": fcm_token, "notification": {"title": data.title, "body": data.body}},
            headers={"Authorization": f"key={FCM_SERVER_KEY}", "Content-Type": "application/json"}
        )
    return {"error": False, "fcm_status": res.status_code}