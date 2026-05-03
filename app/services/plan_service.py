import os
import sys
import json
import hashlib

from app.db.connection import get_db_connection


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# C:\Users\woong\Capston\app\services
# -> C:\Users\woong\Capston
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))

AGENT_APP_PATH = os.path.join(PROJECT_ROOT, "agent", "app")

print("[DEBUG] AGENT_APP_PATH =", AGENT_APP_PATH)
print("[DEBUG] AGENT main.py EXISTS =", os.path.exists(os.path.join(AGENT_APP_PATH, "main.py")))

if AGENT_APP_PATH not in sys.path:
    sys.path.insert(0, AGENT_APP_PATH)

from main import recommend_schedule


def get_user_dogs(user_id: int):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT dog_name, size, is_neutered, vaccination_count
        FROM dogs
        WHERE user_id = %s
        """,
        (user_id,)
    )

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "name": row[0],
            "size": row[1],
            "neutered": row[2],
            "vaccination_count": row[3],
        }
        for row in rows
    ]


def make_source_id(place: dict) -> str:
    """
    AI가 추천한 장소는 외부 source_id가 없으므로
    place_name + address 기반으로 고유값 생성.
    """
    raw = f"{place.get('place_name', '')}|{place.get('address', '')}"
    return "ai_" + hashlib.md5(raw.encode("utf-8")).hexdigest()


def get_or_create_place(cur, place: dict) -> int:
    """
    agent가 추천한 장소를 places에 저장하고 place_id 반환.
    이미 같은 source_id가 있으면 기존 place_id 재사용.
    """
    place_name = place.get("place_name")
    address = place.get("address")
    category = place.get("category", "기타")
    lat = place.get("lat")
    lon = place.get("lon")
    phone = place.get("phone")
    image_url = place.get("image_url")
    opening_hours = place.get("opening_hours")

    if not place_name:
        raise ValueError("추천 장소에 place_name이 없습니다.")

    source_id = make_source_id(place)

    cur.execute(
        """
        SELECT place_id
        FROM places
        WHERE source_id = %s
        """,
        (source_id,)
    )

    row = cur.fetchone()

    if row:
        return row[0]

    cur.execute(
        """
        INSERT INTO places (
            place_name,
            address,
            category,
            lat,
            lon,
            source_id,
            phone,
            opening_hours,
            image_url
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING place_id
        """,
        (
            place_name,
            address,
            category,
            lat,
            lon,
            source_id,
            phone,
            opening_hours,
            image_url,
        )
    )

    return cur.fetchone()[0]


def save_agent_schedule(req, schedule: dict):
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO schedules (
                user_id,
                title,
                start_date,
                end_date,
                companion,
                theme,
                user_message
            )
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
            RETURNING schedule_id
            """,
            (
                req.user_id,
                schedule.get("title"),
                req.start_date,
                req.end_date,
                req.companion,
                json.dumps(req.theme, ensure_ascii=False),
                req.user_message,
            )
        )

        schedule_id = cur.fetchone()[0]

        for day_obj in schedule.get("days", []):
            day_number = day_obj.get("day")

            for slot in day_obj.get("slots", []):
                place_id = get_or_create_place(cur, slot)

                cur.execute(
                    """
                    INSERT INTO schedule_items (
                        schedule_id,
                        place_id,
                        day,
                        time_slot,
                        "order",
                        memo
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        schedule_id,
                        place_id,
                        day_number,
                        slot.get("time_slot"),
                        slot.get("order"),
                        slot.get("memo"),
                    )
                )

                # 응답 JSON에도 저장된 place_id 추가
                slot["place_id"] = place_id

        conn.commit()
        return schedule_id

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        conn.close()


def create_plan(req):
    dogs = get_user_dogs(req.user_id)

    if not dogs:
        return {
            "error": True,
            "msg": "등록된 반려견 정보가 없습니다.",
            "schedule_id": None,
            "schedule": None,
        }

    agent_request = {
        "user_id": req.user_id,
        "start_date": req.start_date,
        "end_date": req.end_date,
        "companion": req.companion,
        "theme": req.theme,
        "user_message": req.user_message,
        "dogs": dogs,
    }

    result = recommend_schedule(agent_request)

    if result.get("error"):
        return {
            "error": True,
            "msg": result.get("error"),
            "schedule_id": None,
            "schedule": None,
            "raw_result": result,
        }

    schedule = result.get("schedule")

    if not schedule:
        return {
            "error": True,
            "msg": "agent가 schedule을 반환하지 않았습니다.",
            "schedule_id": None,
            "schedule": None,
            "raw_result": result,
        }

    schedule_id = save_agent_schedule(req, schedule)

    return {
        "error": False,
        "msg": "일정 생성 및 DB 저장 성공",
        "schedule_id": schedule_id,
        "schedule": schedule,
    }