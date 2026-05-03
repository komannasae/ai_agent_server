from typing import Optional, TypedDict


class DogInfo(TypedDict):
    name: str
    size: str        # "소형" | "중형" | "대형" | "맹견"
    neutered: bool
    vaccination_count: int


class TravelState(TypedDict):
    # ── 입력 (서버팀 전달) ──
    user_id: int
    start_date: str          # "YYYY-MM-DD"
    end_date: str            # "YYYY-MM-DD"
    companion: str           # "혼자" | "커플" | "가족" | "친구"
    theme: list[str]         # ["관광지", "맛집", ...]
    user_message: str        # 자유 텍스트 (없으면 "")
    dogs: list[DogInfo]      # 반려견 정보 리스트

    # ── 에이전트 중간 출력 ──
    candidate_places: list[dict]    # place_search_node 출력
    schedule_plan: Optional[dict]   # schedule_builder_node 출력
    retry_count: int                # validate_schedule_node 재시도 횟수
    validation_issues: list[str]    # validate_schedule_node → schedule_builder_node 피드백

    # ── 최종 출력 ──
    schedule_id: Optional[int]
    result: Optional[dict]
