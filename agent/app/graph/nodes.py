"""
LangGraph 노드 4개

Node 1: place_search_node     — server API 장소 조회 (결정론적)
Node 2: schedule_builder_node — LLM + bind_tools 루프
Node 3: validate_schedule_node — LLM 구조화 출력으로 일정 검증
Node 4: save_schedule_node    — server 저장 전 결과 정리
"""
import copy
import json
import logging
import re
from datetime import date

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from config import OPENAI_API_KEY, SIZE_ORDER
from scripts.server_api_client import get_places_by_ids
from graph.state import TravelState
from tools.place_tools import search_places, semantic_search
from tools.schedule_tools import (
    get_weather, calc_distance_km, find_nearby_places, search_indoor_places,
)

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# LLM 싱글톤 (모듈 로드 시 1회만 생성)
# ──────────────────────────────────────────────

_TOOLS         = [get_weather, calc_distance_km, find_nearby_places, search_indoor_places]
_TOOLS_MAP     = {t.name: t for t in _TOOLS}

_LLM           = ChatOpenAI(model="gpt-4o-mini", api_key=OPENAI_API_KEY, temperature=0.3)
_LLM_WITH_TOOLS = _LLM.bind_tools(_TOOLS)


# ──────────────────────────────────────────────
# Node 1: 장소 검색 (결정론적)
# ──────────────────────────────────────────────

def place_search_node(state: TravelState) -> dict:
    """테마·조건 필터 + 시맨틱 검색으로 후보 장소 수집"""
    themes = state["theme"]
    dogs   = state["dogs"]

    if not dogs:
        raise ValueError("dogs 목록이 비어 있습니다. 반려견 정보를 1개 이상 입력해주세요.")

    biggest_dog     = max(dogs, key=lambda d: SIZE_ORDER.get(d["size"], 1))
    min_vaccination = min(d.get("vaccination_count", 0) for d in dogs)
    any_neutered    = any(d.get("neutered", False) for d in dogs)

    num_days = (date.fromisoformat(state["end_date"]) - date.fromisoformat(state["start_date"])).days + 1

    search_themes = list(themes)
    if num_days > 1 and "숙박" not in search_themes:
        search_themes.append("숙박")

    try:
        places = search_places(
            themes=search_themes,
            dog_size=biggest_dog["size"],
            vaccination_count=min_vaccination,
            is_neutered=any_neutered,
        )

        user_message = state.get("user_message", "").strip()
        if user_message:
            semantic_results = semantic_search(user_message, search_themes)
            existing_ids = {p["place_id"] for p in places}
            for p in semantic_results:
                if p["place_id"] not in existing_ids:
                    places.append(p)
                    existing_ids.add(p["place_id"])
    except Exception as e:
        logger.error("place_search_node 서버 API 조회 중 예외 발생: %s", e)
        raise

    logger.info("후보 장소 %d개 수집 (숙박 자동포함: %s)", len(places), num_days > 1)
    return {"candidate_places": places}


# ──────────────────────────────────────────────
# Node 2: 일정 생성 — ReAct Agent
# ──────────────────────────────────────────────

_SYSTEM_PROMPT = """\
당신은 대전 반려견 동반 여행 일정을 만드는 전문 플래너입니다.

반드시 다음 순서로 작업하세요:
1. get_weather 툴로 여행 기간 날씨를 확인합니다. 조회 실패해도 계속 진행합니다.
2. bad_weather=true인 날이 있으면 search_indoor_places 툴로 실내 장소를 추가 검색합니다.
3. 후보 장소에서 일정 초안을 작성합니다 (하루 최대 4곳).
4. 같은 날 인접한 두 장소(A→B)마다 calc_distance_km 툴로 거리를 확인합니다.
5. 5km를 초과하는 구간이 있으면:
   a. B 장소의 lat, lon으로 find_nearby_places 툴을 호출합니다.
   b. 같은 카테고리 장소가 있으면 교체합니다.
   c. 교체 후 거리를 calc_distance_km으로 재확인합니다.
6. 어떤 툴이 실패해도 반드시 후보 장소를 활용해 최종 JSON을 반환합니다.

반환 형식 (JSON만 반환, 다른 텍스트 없이):
{
  "title": "여행 제목",
  "days": [
    {
      "day": 1,
      "date": "YYYY-MM-DD",
      "slots": [
        {
          "time_slot": "오전|점심|오후|저녁",
          "order": 1,
          "place_id": 123,
          "place_name": "장소명",
          "memo": "한 줄 추천 메모"
        }
      ]
    }
  ]
}

규칙:
- 하루 최소 3개, 최대 4개 장소 (오전·점심·오후·저녁 순서)
- 숙박 배치 (2일 이상 여행):
    * 1일차 저녁, 2일차 저녁, ... (마지막 날을 제외한 전날까지) → 반드시 숙박 장소 배치
    * 마지막 일정은 저녁 이후 숙박일정을 넣지 않는다(예를 들면 1박 2일 일정이면 2일차가 마지막이니 저녁 이후에 숙박을 넣지 않는다)
    * 저녁 슬롯에 숙박 장소를 배치한 경우 → memo에 해당 장소 추천 이유 한 줄 작성
    * 숙박 후보가 없어서 배치하지 못한 경우 → memo에 "숙박 별도 예약 필요" 명시
    * "숙박 별도 예약 필요"는 숙박 장소를 배치하지 못했을 때만 사용하며, 실제 숙박 장소가 배치된 슬롯에는 절대 사용하지 않는다
    * 반드시 첫번째로 선택한 숙박 장소를 유지한다.
- 저녁 슬롯에는 공원보다 맛집·카페·숙박을 우선 배치한다
- 여행 제목은 동행자·테마·요청사항을 반영해 구체적으로 작성한다
- 반려견 조건(크기·백신·중성화) 반드시 준수
"""


def schedule_builder_node(state: TravelState) -> dict:
    """LLM + bind_tools: 날씨 확인 → 실내 장소 보완 → 거리 검증 → 일정 JSON 생성"""
    start    = date.fromisoformat(state["start_date"])
    end      = date.fromisoformat(state["end_date"])
    num_days = (end - start).days + 1

    dog_desc = ", ".join(
        f"{d['name']}({d['size']}, 백신 {d['vaccination_count']}회, "
        f"{'중성화O' if d['neutered'] else '중성화X'})"
        for d in state["dogs"]
    )

    candidates  = state["candidate_places"]
    stay_places = [p for p in candidates if p.get("category") == "숙박"]
    other_places = [p for p in candidates if p.get("category") != "숙박"]

    # 이전 검증에서 발견된 문제가 있으면 피드백으로 포함
    validation_issues = state.get("validation_issues", [])
    feedback_section = ""
    if validation_issues:
        issues_text = "\n".join(f"  - {issue}" for issue in validation_issues)
        feedback_section = f"""
【이전 일정 검토 결과 — 반드시 수정하세요】
{issues_text}
위 문제들을 해결한 새 일정을 작성하세요.
"""

    # user_message에서 핵심 요청 강조 섹션 생성
    user_msg = state.get("user_message", "").strip()
    if user_msg:
        user_request_section = f"""\
【사용자 핵심 요청 — 반드시 반영】
"{user_msg}"
→ 위 요청에 언급된 장소 유형(카페·공원 등)이 후보에 있으면 반드시 우선 선택하세요.
→ 지역(중구 등) 요청이 있으면 해당 지역 장소를 우선 배치하세요.
"""
    else:
        user_request_section = ""

    user_prompt = f"""\
여행 기간: {state['start_date']} ~ {state['end_date']} ({num_days}일)
동행 유형: {state['companion']}
테마: {', '.join(state['theme'])}
반려견: {dog_desc}
{user_request_section}{feedback_section}
【숙박 후보】 (여행 마지막 일정을 제외하고 저녁에 반드시 사용):
{json.dumps(stay_places, ensure_ascii=False, indent=2) if stay_places else '없음 — 숙박 별도 예약 필요'}

【일반 장소 후보】:
{json.dumps(other_places, ensure_ascii=False, indent=2)}
"""

    messages: list = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]

    # 툴 호출 루프 (최대 10회)
    for _ in range(10):
        response = _LLM_WITH_TOOLS.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            break

        for tc in response.tool_calls:
            tool = _TOOLS_MAP.get(tc["name"])
            if tool is None:
                messages.append(ToolMessage(
                    content=f"알 수 없는 툴: {tc['name']}",
                    tool_call_id=tc["id"],
                ))
                continue
            try:
                result = tool.invoke(tc["args"])
            except Exception as e:
                logger.error("툴 실행 실패 (%s): %s", tc["name"], e)
                result = f"툴 실행 오류: {e}"
            messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
            logger.debug("툴 호출: %s → %s", tc["name"], str(result)[:100])

    final_content = response.content
    logger.debug("LLM 최종 응답: %s", final_content[:300])

    json_match = re.search(r"\{[\s\S]*\}", final_content)
    if not json_match:
        raise ValueError(f"LLM이 유효한 JSON을 반환하지 않았습니다:\n{final_content[:500]}")

    plan = json.loads(json_match.group())
    logger.info("일정 생성 완료: %s (%d일)", plan.get("title"), len(plan.get("days", [])))
    return {"schedule_plan": plan}


# ──────────────────────────────────────────────
# Node 3: 일정 검증 — Python 결정론적 + LLM 정성 검증
# ──────────────────────────────────────────────

class _ValidationResult(BaseModel):
    is_valid: bool = Field(description="일정에 문제가 없으면 True")
    issues: list[str] = Field(description="발견된 문제 목록. 문제 없으면 빈 리스트")

_LLM_VALIDATOR = _LLM.with_structured_output(_ValidationResult)


def _python_validate(plan: dict, state: TravelState) -> list[str]:
    """결정론적으로 빠르게 검증할 수 있는 구조적 규칙들"""
    issues: list[str] = []
    days      = plan.get("days", [])
    last_date = state["end_date"]

    # candidate_places로 place_id → category 매핑 (숙박 여부 판단용)
    place_category = {
        p["place_id"]: p.get("category", "")
        for p in state.get("candidate_places", [])
    }

    for day_obj in days:
        day_num = day_obj["day"]
        slots   = day_obj.get("slots", [])
        d_date  = day_obj.get("date", "")

        # 규칙 1: 각 날 최소 3개 슬롯
        if len(slots) < 3:
            issues.append(f"{day_num}일차 슬롯이 {len(slots)}개로 최소 3개 미만입니다.")

        # 규칙 2: 마지막 날 저녁에 숙박 없어야 함
        if d_date == last_date:
            for slot in slots:
                if slot.get("time_slot") == "저녁":
                    cat = place_category.get(slot["place_id"], "")
                    if cat == "숙박":
                        issues.append(
                            f"마지막 날({last_date}) 저녁에 숙박 장소 "
                            f"'{slot['place_name']}'이 배치되어 있습니다."
                        )
        # 규칙 3: 마지막 날 제외 모든 날 저녁에 숙박 배치
        else:
            evening_slots = [s for s in slots if s.get("time_slot") == "저녁"]
            has_stay = any(
                place_category.get(s["place_id"], "") == "숙박"
                for s in evening_slots
            )
            if not has_stay:
                issues.append(
                    f"{day_num}일차({d_date}) 저녁 슬롯에 숙박 장소가 배치되지 않았습니다."
                )

        # 규칙 4: 숙박 장소가 배치된 슬롯 memo에 "숙박 별도 예약 필요" 금지
        for slot in slots:
            cat = place_category.get(slot["place_id"], "")
            if cat == "숙박" and "숙박 별도 예약 필요" in (slot.get("memo") or ""):
                issues.append(
                    f"{day_num}일차 '{slot['place_name']}' 슬롯 — "
                    f"숙박 장소임에도 '숙박 별도 예약 필요' memo가 잘못 기재되어 있습니다."
                )

        # 규칙 5: 같은 날 내 숙박 제외 장소의 place_id 중복 금지
        seen: set[int] = set()
        for slot in slots:
            cat = place_category.get(slot["place_id"], "")
            if cat != "숙박":
                if slot["place_id"] in seen:
                    issues.append(
                        f"{day_num}일차에 '{slot['place_name']}'(place_id={slot['place_id']})이 "
                        f"중복 배치되어 있습니다."
                    )
                seen.add(slot["place_id"])

    return issues


def validate_schedule_node(state: TravelState) -> dict:
    """Python 결정론적 검증 → LLM 정성 검증 순서로 일정 검토"""
    plan        = state["schedule_plan"]
    retry_count = state.get("retry_count", 0)
    themes      = state.get("theme", [])
    user_msg    = state.get("user_message", "").strip()
    num_days    = (date.fromisoformat(state["end_date"]) - date.fromisoformat(state["start_date"])).days + 1

    # ── Step 1: Python 결정론적 검증 ──
    python_issues = _python_validate(plan, state)
    if python_issues:
        if retry_count >= 1:
            logger.warning("일정 검증 최대 재시도 초과 — 현재 일정으로 진행 (Python 규칙 위반: %s)", python_issues)
            return {"retry_count": retry_count, "validation_issues": []}
        logger.warning("Python 검증 실패 (재시도 %d): %s", retry_count + 1, python_issues)
        return {
            "retry_count":       retry_count + 1,
            "schedule_plan":     None,
            "validation_issues": python_issues,
        }

    # ── Step 2: LLM 정성 검증 ──
    user_msg_rule = (
        f'- 사용자 요청사항 "{user_msg}"의 핵심 의도가 일정에 어느 정도 반영되어 있는가? '
        f'완벽하지 않아도 의도가 보이면 통과.'
        if user_msg else ""
    )

    llm_prompt = f"""\
반려견 동반 여행 일정을 검토하고 문제가 있으면 issues에 명시하세요.

[여행 정보]
- 기간: {state['start_date']} ~ {state['end_date']} ({num_days}일)
- 요청 테마: {', '.join(themes)}

[검토 항목]
1. [테마 반영] 요청 테마 {themes} 각각에 해당하는 장소가 전체 일정 통틀어 최소 1개 이상 포함되어 있는가?
   → 특정 날에 없어도 전체 일정에 1개 이상 있으면 통과입니다.
{user_msg_rule}

[주의사항]
- 숙박 배치 규칙은 이미 별도로 검증했으므로 숙박 관련 사항은 지적하지 마세요.
- 위 검토 항목 이외의 사항은 지적하지 마세요.

[일정]
{json.dumps(plan, ensure_ascii=False, indent=2)}
"""

    try:
        result: _ValidationResult = _LLM_VALIDATOR.invoke([HumanMessage(content=llm_prompt)])
    except Exception as e:
        logger.warning("LLM 검증 실패 (검증 생략): %s", e)
        return {"retry_count": retry_count}

    if result.is_valid:
        logger.info("일정 검증 통과 (retry=%d)", retry_count)
        return {"retry_count": retry_count, "validation_issues": []}
    else:
        if retry_count >= 1:
            logger.warning("일정 검증 최대 재시도 초과 — 현재 일정으로 진행 (LLM 검증 실패: %s)", result.issues)
            return {"retry_count": retry_count, "validation_issues": []}
        logger.warning("LLM 검증 실패 (재시도 %d): %s", retry_count + 1, result.issues)
        return {
            "retry_count":       retry_count + 1,
            "schedule_plan":     None,
            "validation_issues": result.issues,
        }


def should_retry_or_save(state: TravelState) -> str:
    """검증 결과에 따라 재생성 또는 저장 분기"""
    if state.get("schedule_plan") is None:
        return "retry"
    return "save"


# ──────────────────────────────────────────────
# Node 4: DB 저장 (결정론적)
# ──────────────────────────────────────────────

def save_schedule_node(state: TravelState) -> dict:
    """
    agent 내부에서는 DB에 저장하지 않는다.

    생성된 일정에 place 상세 정보만 server API로 보강해서 반환한다.
    실제 schedules / schedule_items 저장은 server의 plan_service.save_agent_schedule()이 담당한다.
    """
    plan = state["schedule_plan"]
    place_ids = [slot["place_id"] for day in plan.get("days", []) for slot in day.get("slots", [])]

    try:
        place_map = get_places_by_ids(place_ids)
    except Exception as e:
        logger.error("장소 상세 조회 서버 API 호출 실패: %s", e)
        place_map = {}

    enriched_plan = copy.deepcopy(plan)
    for day in enriched_plan.get("days", []):
        for slot in day.get("slots", []):
            info = place_map.get(slot.get("place_id"), {})
            slot["lat"]           = info.get("lat")
            slot["lon"]           = info.get("lon")
            slot["address"]       = info.get("address")
            slot["category"]      = info.get("category")
            slot["phone"]         = info.get("phone")
            slot["image_url"]     = info.get("image_url")
            slot["opening_hours"] = info.get("opening_hours")

    logger.info("agent 일정 생성 완료 — DB 저장은 server가 수행")
    return {
        "result": {
            "schedule_id": None,
            "schedule": enriched_plan,
        },
    }
