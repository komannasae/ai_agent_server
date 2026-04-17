from fastapi import APIRouter, HTTPException
from model import ScheduleWeatherRequest
from agent.weather import (
    get_weather,
    _DAEJEON_LAT,
    _DAEJEON_LON,
    _dust_level,
    _ozone_level,
    _is_dog_walk_ok,
    _WMO,
)
import httpx
import asyncio
import json

router = APIRouter()


# ============================
# 날씨 비동기 호출
# ============================
async def _fetch_weather(lat: float, lng: float) -> dict:
    async with httpx.AsyncClient() as client:
        res = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude":  lat,
                "longitude": lng,
                "current":   "temperature_2m,precipitation,weathercode,windspeed_10m,relative_humidity_2m",
                "timezone":  "Asia/Seoul",
            },
            timeout=10
        )
    if res.status_code != 200:
        raise HTTPException(status_code=502, detail="날씨 API 호출 실패")
    return res.json().get("current", {})


# ============================
# 대기질 비동기 호출
# ============================
async def _fetch_air(lat: float, lng: float) -> dict:
    async with httpx.AsyncClient() as client:
        res = await client.get(
            "https://air-quality-api.open-meteo.com/v1/air-quality",
            params={
                "latitude":  lat,
                "longitude": lng,
                "current":   "pm10,ozone",
                "timezone":  "Asia/Seoul",
            },
            timeout=10
        )
    if res.status_code != 200:
        return {"pm10": None, "ozone": None}
    return res.json().get("current", {})


# ============================
# 응답 형식 조립
# ============================
def _build_response(weather: dict, air: dict) -> dict:
    temp      = weather.get("temperature_2m", 0)
    rain      = weather.get("precipitation", 0)
    windspeed = weather.get("windspeed_10m", 0)
    humidity  = weather.get("relative_humidity_2m", 0)
    code      = weather.get("weathercode", 0)
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


# ============================
# GET /weather/current
# 특정 좌표 현재 날씨
# ============================
@router.get("/current")
async def get_weather_current(lat: float, lng: float):
    weather, air = await asyncio.gather(
        _fetch_weather(lat, lng),
        _fetch_air(lat, lng)
    )
    return _build_response(weather, air)


# ============================
# GET /weather/daejeon
# 대전 현재 날씨 — Flutter UI 메인
# ============================
@router.get("/daejeon")
async def get_daejeon_weather():
    weather, air = await asyncio.gather(
        _fetch_weather(_DAEJEON_LAT, _DAEJEON_LON),
        _fetch_air(_DAEJEON_LAT, _DAEJEON_LON)
    )
    return _build_response(weather, air)


# ============================
# GET /weather/daejeon/daily
# 대전 기간별 날씨 — AI 에이전트 + Flutter 일정 화면
# 예시: GET /weather/daejeon/daily?start_date=2026-04-18&end_date=2026-04-20
# ============================
@router.get("/daejeon/daily")
def get_daejeon_daily(start_date: str, end_date: str):
    result = get_weather(start_date, end_date)
    return {"error": False, "daily": json.loads(result)}


# ============================
# POST /weather/schedule-check
# 스케줄 날짜 날씨 확인 + 강아지 산책 가능 여부
# ============================
@router.post("/schedule-check")
async def schedule_weather_check(data: ScheduleWeatherRequest):
    weather, air = await asyncio.gather(
        _fetch_weather(data.lat, data.lng),
        _fetch_air(data.lat, data.lng)
    )
    temp      = weather.get("temperature_2m", 0)
    rain      = weather.get("precipitation", 0)
    windspeed = weather.get("windspeed_10m", 0)
    code      = weather.get("weathercode", 0)
    walk_info = _is_dog_walk_ok(temp, rain, windspeed, code)

    return {
        "date":    data.schedule_date,
        "weather": _build_response(weather, air),
        "alert":   not walk_info["walkable"],
    }