from model import EvaluateRequest
from agent.travel_agent import recommend_trip_agent
from routers.weather import fetch_weather, is_dog_walk_ok

async def evaluate_and_retry(data: EvaluateRequest, max_retries: int = 3) -> dict:
    """
    조건 판단 반복 조사
    흐름: 장소 추천 → 날씨 확인 → 조건 미충족 시 재추천 (최대 max_retries회)
    """
    for attempt in range(max_retries):
        # 1. 여행 추천
        recommend = await recommend_trip_agent(
            destination=data.destination,
            dog_size=data.dog_size,
            start_date="",
            end_date=""
        )

        # 2. TODO: 추천 장소의 lat/lng 가져오기
        lat, lng = 37.5665, 126.9780  # 임시값

        # 3. 날씨 확인
        current   = await fetch_weather(lat, lng)
        walk_info = is_dog_walk_ok(
            current.get("temperature_2m", 0),
            current.get("precipitation", 0),
            current.get("windspeed_10m", 0),
            current.get("weathercode", 0),
        )

        # 4. 조건 충족 시 반환
        if walk_info["walkable"]:
            return {"attempt": attempt + 1, "recommend": recommend, "weather": walk_info}

        print(f"[evaluator] {attempt + 1}회 재조사 중... 이유: {walk_info['issues']}")

    return {"attempt": max_retries, "recommend": recommend, "weather": walk_info, "warning": "최대 재시도 초과"}