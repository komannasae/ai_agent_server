from fastapi import APIRouter
from app.models.plan import PlanCreateRequest
from app.services.plan_service import create_plan

router = APIRouter(
    prefix="/plans",
    tags=["plans"]
)


@router.post("")
def create_travel_plan(req: PlanCreateRequest):
    return create_plan(req)

# 테스트용 엔드포인트 - 실제 서비스에서는 제거 예정
@router.post("/plans/test-save")
def test_save_plan():
    from types import SimpleNamespace
    from app.services.plan_service import save_agent_schedule

    req = SimpleNamespace(
        user_id=4,
        start_date="2026-05-10",
        end_date="2026-05-11",
        companion="가족",
        theme=["카페", "관광지"],
        user_message="Swagger 저장 테스트용 더미 일정",
    )

    dummy_schedule = {
        "title": "Swagger 저장 테스트 일정",
        "days": [
            {
                "day": 1,
                "slots": [
                    {
                        "place_name": "테스트 반려견 카페",
                        "address": "대전광역시 테스트구 테스트로 1",
                        "category": "카페",
                        "lat": 36.3504,
                        "lon": 127.3845,
                        "phone": "042-000-0000",
                        "opening_hours": "10:00-20:00",
                        "image_url": None,
                        "time_slot": "오전",
                        "order": 1,
                        "memo": "Swagger 저장 테스트용 장소",
                    },
                    {
                        "place_name": "테스트 산책 공원",
                        "address": "대전광역시 테스트구 공원로 2",
                        "category": "관광지",
                        "lat": 36.3510,
                        "lon": 127.3850,
                        "phone": None,
                        "opening_hours": "상시",
                        "image_url": None,
                        "time_slot": "오후",
                        "order": 2,
                        "memo": "두 번째 저장 테스트 장소",
                    },
                ],
            }
        ],
    }

    schedule_id = save_agent_schedule(req, dummy_schedule)

    return {
        "message": "저장 테스트 성공",
        "schedule_id": schedule_id,
        "schedule": dummy_schedule,
    }