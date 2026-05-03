"""
schedule_builder_node에서 LLM이 동적으로 호출하는 LangChain 툴 4개

- get_weather         : Open-Meteo로 대전 날씨 조회 (무료, API 키 불필요)
- calc_distance_km    : Haversine 공식으로 두 좌표 간 직선거리 계산
- find_nearby_places  : 특정 좌표 반경 내 대안 장소 검색 (거리 초과 시 교체용)
- search_indoor_places: 날씨 나쁠 때 실내 입장 가능 장소 검색
"""
import json
import logging
import math

import requests
from langchain_core.tools import tool

from scripts.server_api_client import (
    find_nearby_places as request_nearby_places,
    search_indoor_places as request_indoor_places,
)

logger = logging.getLogger(__name__)

# 대전광역시 중심 좌표
_DAEJEON_LAT = 36.3504
_DAEJEON_LON = 127.3845

# Open-Meteo WMO 날씨 코드 → 한국어 설명
_WMO: dict[int, str] = {
    0: "맑음", 1: "대체로 맑음", 2: "부분 흐림", 3: "흐림",
    45: "안개", 48: "안개",
    51: "이슬비(약)", 53: "이슬비", 55: "이슬비(강)",
    61: "비(약)", 63: "비", 65: "비(강)",
    71: "눈(약)", 73: "눈", 75: "눈(강)",
    80: "소나기(약)", 81: "소나기", 82: "소나기(강)",
    95: "뇌우",
}


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine 공식으로 두 좌표 간 직선거리(km) 반환"""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return round(2 * R * math.asin(math.sqrt(a)), 2)


# ──────────────────────────────────────────────
# Tool 1: 날씨 조회
# ──────────────────────────────────────────────

@tool
def get_weather(start_date: str, end_date: str) -> str:
    """대전의 날씨를 조회합니다.
    start_date ~ end_date 기간 동안 날짜별 날씨와 강수량을 반환합니다.
    bad_weather=true인 날은 실내 장소를 우선 배치해야 합니다."""
    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude":   _DAEJEON_LAT,
                "longitude":  _DAEJEON_LON,
                "daily":      "weather_code,precipitation_sum",
                "start_date": start_date,
                "end_date":   end_date,
                "timezone":   "Asia/Seoul",
            },
            timeout=10,
        )
        resp.raise_for_status()
        daily = resp.json()["daily"]

        result = []
        for i, d in enumerate(daily["time"]):
            code   = daily["weather_code"][i] or 0
            precip = daily["precipitation_sum"][i] or 0.0
            bad    = code >= 51 or precip > 0.5
            result.append({
                "date":             d,
                "weather":          _WMO.get(code, f"코드{code}"),
                "precipitation_mm": precip,
                "bad_weather":      bad,
                "recommendation":   "실내 장소 우선 배치" if bad else "실외 장소 가능",
            })
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.warning("날씨 조회 실패 (일정 생성 계속): %s", e)
        return json.dumps([
            {"date": start_date, "weather": "조회 실패", "bad_weather": False,
             "recommendation": "날씨 정보 없음 — 실외 장소로 진행"},
        ], ensure_ascii=False)


# ──────────────────────────────────────────────
# Tool 2: 거리 계산
# ──────────────────────────────────────────────

@tool
def calc_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 장소의 위도/경도로 직선거리(km)를 계산합니다 (Haversine 공식).
    같은 날 방문할 장소끼리 거리가 5km를 초과하면 동선이 불편합니다.
    초과 시 find_nearby_places로 더 가까운 대안 장소를 찾으세요."""
    try:
        if not (-90 <= lat1 <= 90 and -90 <= lat2 <= 90 and -180 <= lon1 <= 180 and -180 <= lon2 <= 180):
            logger.warning("잘못된 좌표값: (%s,%s)→(%s,%s)", lat1, lon1, lat2, lon2)
            return -1.0
        return _haversine(lat1, lon1, lat2, lon2)
    except Exception as e:
        logger.error("거리 계산 실패: %s", e)
        return -1.0


# ──────────────────────────────────────────────
# Tool 3: 가까운 대안 장소 검색
# ──────────────────────────────────────────────

@tool
def find_nearby_places(
    lat: float,
    lon: float,
    themes: list[str],
    max_km: float = 5.0,
) -> str:
    """특정 좌표(lat, lon)에서 max_km 이내의 반려견 동반 장소를 반환합니다.
    거리가 초과된 장소의 대안을 찾을 때 사용하세요.
    반환된 목록에서 가장 가깝고 적합한 장소를 선택해 교체하세요."""
    try:
        results = request_nearby_places(
            lat=lat,
            lon=lon,
            themes=themes,
            max_km=max_km,
        )
        logger.debug("find_nearby_places: %d개 반환 (반경 %.1fkm)", len(results), max_km)
        return json.dumps(results, ensure_ascii=False)
    except Exception as e:
        logger.error("근처 장소 검색 실패: %s", e)
        return json.dumps([], ensure_ascii=False)


# ──────────────────────────────────────────────
# Tool 4: 실내 장소 재검색
# ──────────────────────────────────────────────

@tool
def search_indoor_places(
    themes: list[str],
    dog_size: str = "소형",
    vaccination_count: int = 0,
    is_neutered: bool = False,
) -> str:
    """날씨가 나쁠 때 실내(indoor=True) 반려견 동반 장소를 검색합니다.
    bad_weather 날에 배치할 후보를 선택하세요.
    dog_size: 소형|중형|대형|맹견, themes 예시: ["맛집", "문화시설"]"""
    try:
        results = request_indoor_places(
            themes=themes,
            dog_size=dog_size,
            vaccination_count=vaccination_count,
            is_neutered=is_neutered,
        )
        logger.debug("search_indoor_places: %d개 반환", len(results))
        return json.dumps(results, ensure_ascii=False)
    except Exception as e:
        logger.error("실내 장소 검색 실패: %s", e)
        return json.dumps([], ensure_ascii=False)
