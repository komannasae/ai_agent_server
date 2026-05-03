import json
import math
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.db.connection import get_db_connection

router = APIRouter(prefix="/internal/places", tags=["internal-places"])

SIZE_ORDER = {"소형": 1, "중형": 2, "대형": 3, "맹견": 4}


class PlaceSearchRequest(BaseModel):
    themes: list[str] = Field(default_factory=list)
    dog_size: str = "소형"
    vaccination_count: int = 0
    is_neutered: bool = False
    limit: int = 60


class SemanticSearchRequest(BaseModel):
    query_embedding: list[float]
    themes: list[str] = Field(default_factory=list)
    top_k: int = 20


class NearbySearchRequest(BaseModel):
    lat: float
    lon: float
    themes: list[str] = Field(default_factory=list)
    max_km: float = 5.0


class IndoorSearchRequest(BaseModel):
    themes: list[str] = Field(default_factory=list)
    dog_size: str = "소형"
    vaccination_count: int = 0
    is_neutered: bool = False
    limit: int = 20


class PlaceIdsRequest(BaseModel):
    place_ids: list[int] = Field(default_factory=list)


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(str(float(v)) for v in values) + "]"


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return round(2 * r * math.asin(math.sqrt(a)), 2)


def _place_to_dict(row: dict[str, Any]) -> dict[str, Any]:
    data = {
        "place_id": row.get("place_id"),
        "place_name": row.get("place_name"),
        "address": row.get("address"),
        "category": row.get("category"),
        "lat": row.get("lat"),
        "lon": row.get("lon"),
        "phone": row.get("phone"),
        "opening_hours": row.get("opening_hours"),
        "image_url": row.get("image_url"),
        "rating": row.get("rating"),
        "parking_available": row.get("parking_available"),
    }

    if row.get("condition_id") is not None:
        data["conditions"] = {
            "allowed": row.get("allowed"),
            "indoor": row.get("indoor"),
            "terrace_only": row.get("terrace_only"),
            "carrier_required": row.get("carrier_required"),
            "leash_required": row.get("leash_required"),
            "size_limit": row.get("size_limit"),
            "weight_limit": row.get("weight_limit"),
            "vaccination_required": row.get("vaccination_required"),
            "neutered_required": row.get("neutered_required"),
            "dog_count_limit": row.get("dog_count_limit"),
        }
    return data


def _rows_to_places(rows) -> list[dict[str, Any]]:
    return [_place_to_dict(dict(row)) for row in rows]


def _passes_dog_condition(place: dict[str, Any], dog_size: str, vaccination_count: int, is_neutered: bool) -> bool:
    cond: Optional[dict[str, Any]] = place.get("conditions")
    if not cond:
        return True

    if cond.get("allowed") is False:
        return False

    size_limit = cond.get("size_limit")
    if size_limit and size_limit != "없음":
        if SIZE_ORDER.get(dog_size, 1) > SIZE_ORDER.get(size_limit, 4):
            return False

    required_vaccination = cond.get("vaccination_required") or 0
    if required_vaccination and vaccination_count < required_vaccination:
        return False

    if cond.get("neutered_required") and not is_neutered:
        return False

    return True


def _select_base_places(where_sql: str, params: tuple[Any, ...], order_sql: str = "p.place_id ASC", limit_sql: str = ""):
    sql = f"""
        SELECT
            p.place_id, p.place_name, p.address, p.category, p.lat, p.lon,
            p.phone, p.opening_hours, p.image_url, 0 AS rating, p.parking_available,
            pc.condition_id, pc.allowed, pc.indoor, pc.terrace_only,
            pc.carrier_required, pc.leash_required, pc.size_limit, pc.weight_limit,
            pc.vaccination_required, pc.neutered_required, pc.dog_count_limit
        FROM places p
        LEFT JOIN place_conditions pc ON p.place_id = pc.place_id
        WHERE {where_sql}
        ORDER BY {order_sql}
        {limit_sql}
    """
    conn = get_db_connection()
    try:
        with conn.cursor(row_factory=None) as cur:
            cur.execute(sql, params)
            cols = [desc[0] for desc in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        conn.close()


@router.post("/search")
def search_places(req: PlaceSearchRequest):
    if not req.themes:
        return {"places": []}

    rows = _select_base_places("p.category = ANY(%s)", (req.themes,))
    places = []
    for row in rows:
        place = _place_to_dict(row)
        if not _passes_dog_condition(place, req.dog_size, req.vaccination_count, req.is_neutered):
            continue
        places.append(place)
        if len(places) >= req.limit:
            break
    return {"places": places}


@router.post("/semantic-search")
def semantic_search_places(req: SemanticSearchRequest):
    if not req.themes or not req.query_embedding:
        return {"places": []}

    vector = _vector_literal(req.query_embedding)
    rows = _select_base_places(
        "p.category = ANY(%s) AND p.embedding IS NOT NULL",
        (req.themes, vector),
        order_sql="p.embedding <=> %s::vector",
        limit_sql="LIMIT %s" % int(req.top_k),
    )
    return {"places": _rows_to_places(rows)}


@router.post("/nearby")
def find_nearby_places(req: NearbySearchRequest):
    if not req.themes:
        return {"places": []}
    if not (-90 <= req.lat <= 90 and -180 <= req.lon <= 180):
        raise HTTPException(status_code=400, detail="잘못된 좌표입니다.")

    delta_lat = req.max_km / 111.0
    delta_lon = req.max_km / (111.0 * math.cos(math.radians(req.lat)))

    rows = _select_base_places(
        "p.category = ANY(%s) AND p.lat BETWEEN %s AND %s AND p.lon BETWEEN %s AND %s",
        (req.themes, req.lat - delta_lat, req.lat + delta_lat, req.lon - delta_lon, req.lon + delta_lon),
    )

    results = []
    for row in rows:
        place = _place_to_dict(row)
        if place.get("lat") is None or place.get("lon") is None:
            continue
        dist = _haversine(req.lat, req.lon, place["lat"], place["lon"])
        if dist <= req.max_km:
            results.append({**place, "distance_km": dist})
    results.sort(key=lambda x: x["distance_km"])
    return {"places": results[:10]}


@router.post("/indoor")
def search_indoor_places(req: IndoorSearchRequest):
    if not req.themes:
        return {"places": []}

    rows = _select_base_places(
        "p.category = ANY(%s) AND pc.indoor IS TRUE AND pc.allowed IS TRUE",
        (req.themes,),
    )
    places = []
    for row in rows:
        place = _place_to_dict(row)
        if not _passes_dog_condition(place, req.dog_size, req.vaccination_count, req.is_neutered):
            continue
        places.append(place)
        if len(places) >= req.limit:
            break
    return {"places": places}


@router.post("/by-ids")
def get_places_by_ids(req: PlaceIdsRequest):
    ids = list(dict.fromkeys(req.place_ids))
    if not ids:
        return {"places": {}}

    rows = _select_base_places("p.place_id = ANY(%s)", (ids,))
    return {"places": {str(row["place_id"]): _place_to_dict(row) for row in rows}}
