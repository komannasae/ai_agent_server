"""
서버팀 진입점.

중요:
- agent는 DB에 직접 연결하지 않는다.
- 장소 검색/조회는 FastAPI 서버의 /internal/places/* API를 호출한다.
- 일정 DB 저장은 server/app/services/plan_service.py가 담당한다.
"""
import json
import logging

from graph.graph import travel_graph

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def recommend_schedule(request: dict) -> dict:
    try:
        initial_state = {
            "user_id":      request.get("user_id"),
            "start_date":   request.get("start_date"),
            "end_date":     request.get("end_date"),
            "companion":    request.get("companion", "혼자"),
            "theme":        request.get("theme", ["관광지"]),
            "user_message": request.get("user_message", ""),
            "dogs":         request.get("dogs", []),
            "candidate_places":  [],
            "schedule_plan":     None,
            "retry_count":       0,
            "validation_issues": [],
            "schedule_id":       None,
            "result":            None,
        }

        if not initial_state["user_id"] or not initial_state["start_date"] or not initial_state["end_date"]:
            raise ValueError("필수 입력값 누락 (user_id, start_date, end_date)")

        final_state = travel_graph.invoke(initial_state)
        result = final_state.get("result")
        if result is None:
            raise RuntimeError("그래프 실행 완료 후 result가 None입니다.")

        return result

    except Exception as e:
        logger.exception("recommend_schedule 최종 실패: %s", e)
        return {"error": str(e), "schedule_id": None, "schedule": None}


if __name__ == "__main__":
    test_request = {
        "user_id": 1,
        "start_date": "2026-04-20",
        "end_date": "2026-04-21",
        "companion": "커플",
        "theme": ["관광지", "맛집"],
        "user_message": "중구 쪽으로 공원하고 조용한 카페 위주로 가고 싶어",
        "dogs": [
            {
                "name": "초코",
                "size": "소형",
                "neutered": True,
                "vaccination_count": 3,
            }
        ],
    }

    result = recommend_schedule(test_request)
    print(json.dumps(result, ensure_ascii=False, indent=2))
