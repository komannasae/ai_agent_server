from fastapi import APIRouter
from database import get_db
from models import ChatRequest

router = APIRouter()

@router.post("/send")
def send_chat(data: ChatRequest):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO ai_chats (user_id, trip_id, message, role) VALUES (%s, %s, %s, 'user')",
            (data.user_id, data.trip_id, data.message)
        )
        conn.commit()

    # TODO: AI 응답 생성 → role='assistant'로 저장
    return {"result": "ok", "reply": "AI 응답 대기 중..."}


@router.get("/history/{trip_id}")
def get_history(trip_id: int):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM ai_chats WHERE trip_id=%s ORDER BY created_at ASC",
            (trip_id,)
        )
        rows = cur.fetchall()

    return {"history": rows}
