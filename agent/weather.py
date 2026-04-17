import requests
import json
import logging

logger = logging.getLogger(__name__)

# ============================
# 대전광역시 중심 좌표
# ============================
_DAEJEON_LAT = 36.3504
_DAEJEON_LON = 127.3845

# ============================
# WMO 날씨 코드
# ============================
_WMO: dict[int, str] = {
    0: "맑음", 1: "대체로 맑음", 2: "부분 흐림", 3: "흐림",
    45: "안개", 48: "안개",
    51: "이슬비(약)", 53: "이슬비", 55: "이슬비(강)",
    61: "비(약)", 63: "비", 65: "비(강)",
    71: "눈(약)", 73: "눈", 75: "눈(강)",
    80: "소나기(약)", 81: "소나기", 82: "소나기(강)",
    95: "뇌우",
}


# ============================
# 미세먼지 등급
# ============================
def _dust_level(pm10: float) -> str:
    if pm10 is None:  return "알 수 없음"
    if pm10 <= 30:    return f"좋음 ({pm10}㎍/㎥)"
    if pm10 <= 80:    return f"보통 ({pm10}㎍/㎥)"
    if pm10 <= 150:   return f"나쁨 ({pm10}㎍/㎥)"
    return                   f"매우나쁨 ({pm10}㎍/㎥)"


# ============================
# 오존 등급
# ============================
def _ozone_level(o3: float) -> str:
    if o3 is None:    return "알 수 없음"
    if o3 <= 60:      return f"좋음 ({o3}㎍/㎥)"
    if o3 <= 100:     return f"보통 ({o3}㎍/㎥)"
    if o3 <= 180:     return f"나쁨 ({o3}㎍/㎥)"
    return                   f"매우나쁨 ({o3}㎍/㎥)"


# ============================
# 강아지 산책 가능 여부
# ============================
def _is_dog_walk_ok(temp: float, rain: float, windspeed: float, code: int) -> dict:
    issues = []
    if temp < 0:
        issues.append("기온이 너무 낮아요 (0°C 미만)")
    elif temp > 35:
        issues.append("기온이 너무 높아요 (35°C 초과, 발바닥 화상 위험)")
    if rain > 0:
        issues.append(f"강수량 {rain}mm — 우비/방수 패드 챙기세요")
    if windspeed > 40:
        issues.append(f"강풍 {windspeed}km/h — 소형견 외출 주의")
    if code in (65, 75, 82, 95, 96, 99):
        issues.append("악천후 — 외출 자제 권장")
    return {"walkable": len(issues) == 0, "issues": issues}


# ============================
# 기간별 날씨 — AI 에이전트용
# ============================
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
            {
                "date":             start_date,
                "weather":          "조회 실패",
                "bad_weather":      False,
                "recommendation":   "날씨 정보 없음 — 실외 장소로 진행"
            },
        ], ensure_ascii=False)


# ============================
# 현재 날씨 — Flutter UI용
# ============================
def get_current_weather() -> dict:
    """대전 현재 날씨 + 미세먼지 + 오존 조회"""
    try:
        weather_resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude":  _DAEJEON_LAT,
                "longitude": _DAEJEON_LON,
                "current":   "temperature_2m,precipitation,weathercode,windspeed_10m,relative_humidity_2m",
                "timezone":  "Asia/Seoul",
            },
            timeout=10,
        )
        air_resp = requests.get(
            "https://air-quality-api.open-meteo.com/v1/air-quality",
            params={
                "latitude":  _DAEJEON_LAT,
                "longitude": _DAEJEON_LON,
                "current":   "pm10,ozone",
                "timezone":  "Asia/Seoul",
            },
            timeout=10,
        )

        weather_resp.raise_for_status()
        current = weather_resp.json().get("current", {})
        air     = air_resp.json().get("current", {}) if air_resp.status_code == 200 else {}

        temp      = current.get("temperature_2m", 0)
        rain      = current.get("precipitation", 0)
        windspeed = current.get("windspeed_10m", 0)
        humidity  = current.get("relative_humidity_2m", 0)
        code      = current.get("weathercode", 0)
        pm10      = air.get("pm10")
        ozone     = air.get("ozone")

        return {
            "weather":     _WMO.get(code, "알 수 없음"),
            "temperature": f"{temp}°C",
            "dust":        _dust_level(pm10),
            "humidity":    f"{humidity}%",
            "wind":        f"{windspeed}km/h",
            "ozone":       _ozone_level(ozone),
            "dog_walk":    _is_dog_walk_ok(temp, rain, windspeed, code),
        }

    except Exception as e:
        logger.warning("현재 날씨 조회 실패: %s", e)
        return {
            "weather":     "조회 실패",
            "temperature": "-",
            "dust":        "-",
            "humidity":    "-",
            "wind":        "-",
            "ozone":       "-",
            "dog_walk":    {"walkable": False, "issues": ["날씨 정보 조회 실패"]},
        }