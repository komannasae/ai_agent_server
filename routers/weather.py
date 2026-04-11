from fastapi import APIRouter, HTTPException
from model import ScheduleWeatherRequest
from Db import get_schedules_by_trip
import httpx
import asyncio

router = APIRouter()

WMO_CODES = {
    0: "맑음", 1: "대체로 맑음", 2: "부분적으로 흐림", 3: "흐림",
    45: "안개", 48: "착빙 안개",
    51: "약한 이슬비", 53: "보통 이슬비", 55: "강한 이슬비",
    61: "약한 비", 63: "보통 비", 65: "강한 비",
    71: "약한 눈", 73: "보통 눈", 75: "강한 눈",
    80: "소나기(약)", 81: "소나기(보통)", 82: "소나기(강)",
    95: "뇌우", 96: "뇌우+우박", 99: "강한 뇌우+우박",
}

def dust_level(pm10: float) -> str:
    if pm10 is None:  return "알 수 없음"
    if pm10 <= 30:    return f"좋음 ({pm10}㎍/㎥)"
    if pm10 <= 80:    return f"보통 ({pm10}㎍/㎥)"
    if pm10 <= 150:   return f"나쁨 ({pm10}㎍/㎥)"
    return                   f"매우나쁨 ({pm10}㎍/㎥)"

def ozone_level(o3: float) -> str:
    if o3 is None:    return "알 수 없음"
    if o3 <= 60:      return f"좋음 ({o3}㎍/㎥)"
    if o3 <= 100:     return f"보통 ({o3}㎍/㎥)"
    if o3 <= 180:     return f"나쁨 ({o3}㎍/㎥)"
    return                   f"매우나쁨 ({o3}㎍/㎥)"

def is_dog_walk_ok(temp: float, rain: float, windspeed: float, code: int) -> dict:
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

async def fetch_weather(lat: float, lng: float) -> dict:
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

async def fetch_air_quality(lat: float, lng: float) -> dict:
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

@router.get("/current")
async def get_weather(lat: float, lng: float):
    weather_data, air_data = await asyncio.gather(
        fetch_weather(lat, lng),
        fetch_air_quality(lat, lng)
    )
    temp      = weather_data.get("temperature_2m", 0)
    rain      = weather_data.get("precipitation", 0)
    windspeed = weather_data.get("windspeed_10m", 0)
    humidity  = weather_data.get("relative_humidity_2m", 0)
    code      = weather_data.get("weathercode", 0)
    pm10      = air_data.get("pm10")
    ozone     = air_data.get("ozone")
    return {
        "weather":     WMO_CODES.get(code, "알 수 없음"),
        "temperature": f"{temp}°C",
        "dust":        dust_level(pm10),
        "humidity":    f"{humidity}%",
        "wind":        f"{windspeed}km/h",
        "ozone":       ozone_level(ozone),
        "dog_walk":    is_dog_walk_ok(temp, rain, windspeed, code),
    }

@router.post("/schedule-check")
async def schedule_weather_check(data: ScheduleWeatherRequest):
    schedules = get_schedules_by_trip(data.trip_id, data.schedule_date)
    weather_data, air_data = await asyncio.gather(
        fetch_weather(data.lat, data.lng),
        fetch_air_quality(data.lat, data.lng)
    )
    walk_info = is_dog_walk_ok(
        weather_data.get("temperature_2m", 0),
        weather_data.get("precipitation", 0),
        weather_data.get("windspeed_10m", 0),
        weather_data.get("weathercode", 0),
    )
    return {
        "schedules": schedules,
        "weather":   walk_info,
        "alert":     not walk_info["walkable"]
    }