"""
Agent → FastAPI 서버 내부 API 클라이언트.

원칙:
- agent는 DB에 직접 접근하지 않는다.
- 장소 검색/조회가 필요하면 server API를 호출한다.
"""
import logging
from typing import Any

import requests

from config import SERVER_API_BASE_URL

logger = logging.getLogger(__name__)


def _post(path: str, payload: dict[str, Any], timeout: int = 30) -> dict[str, Any]:
    url = f"{SERVER_API_BASE_URL.rstrip('/')}{path}"
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.error("서버 API 호출 실패: %s payload=%s error=%s", url, payload, e)
        raise


def search_places(
    themes: list[str],
    dog_size: str,
    vaccination_count: int,
    is_neutered: bool,
    limit: int = 60,
) -> list[dict]:
    data = _post("/internal/places/search", {
        "themes": themes,
        "dog_size": dog_size,
        "vaccination_count": vaccination_count,
        "is_neutered": is_neutered,
        "limit": limit,
    })
    return data.get("places", [])


def semantic_search_places(
    query_embedding: list[float],
    themes: list[str],
    top_k: int = 20,
) -> list[dict]:
    data = _post("/internal/places/semantic-search", {
        "query_embedding": query_embedding,
        "themes": themes,
        "top_k": top_k,
    }, timeout=60)
    return data.get("places", [])


def find_nearby_places(
    lat: float,
    lon: float,
    themes: list[str],
    max_km: float = 5.0,
) -> list[dict]:
    data = _post("/internal/places/nearby", {
        "lat": lat,
        "lon": lon,
        "themes": themes,
        "max_km": max_km,
    })
    return data.get("places", [])


def search_indoor_places(
    themes: list[str],
    dog_size: str = "소형",
    vaccination_count: int = 0,
    is_neutered: bool = False,
    limit: int = 20,
) -> list[dict]:
    data = _post("/internal/places/indoor", {
        "themes": themes,
        "dog_size": dog_size,
        "vaccination_count": vaccination_count,
        "is_neutered": is_neutered,
        "limit": limit,
    })
    return data.get("places", [])


def get_places_by_ids(place_ids: list[int]) -> dict[int, dict]:
    data = _post("/internal/places/by-ids", {"place_ids": place_ids})
    raw = data.get("places", {})
    return {int(k): v for k, v in raw.items()}
