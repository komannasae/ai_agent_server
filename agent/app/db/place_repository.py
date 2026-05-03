import datetime
import logging
from typing import Optional

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from config import SIZE_ORDER
from db.models import Place, PlaceCondition  # PlaceCondition은 조인 쿼리에만 사용

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# CREATE
# ──────────────────────────────────────────────

def create_place(session: Session, data: dict) -> Place:
    """장소 생성"""
    try:
        place = Place(**data)
        session.add(place)
        session.flush()
        return place
    except SQLAlchemyError as e:
        logger.error("장소 생성 실패 (data=%s): %s", data.get("source_id"), e)
        raise


# ──────────────────────────────────────────────
# READ
# ──────────────────────────────────────────────

def get_place_by_source_id(session: Session, source_id: str) -> Optional[Place]:
    """source_id로 장소 단건 조회"""
    try:
        return session.query(Place).filter_by(source_id=source_id).first()
    except SQLAlchemyError as e:
        logger.error("장소 조회 실패 (source_id=%s): %s", source_id, e)
        raise


def get_places_by_themes(
    session: Session,
    themes: list[str],
    dog_size: str,
    vaccination_count: int,
    is_neutered: bool,
    limit: int = 60,
) -> list[dict]:
    """테마 + 반려견 조건에 맞는 장소 목록 조회"""
    try:
        dog_size_rank = SIZE_ORDER.get(dog_size, 1)

        rows = (
            session.query(Place, PlaceCondition)
            .outerjoin(PlaceCondition, Place.place_id == PlaceCondition.place_id)
            .filter(Place.category.in_(themes))
            .all()
        )

        results = []
        for place, cond in rows:
            if cond:
                if not cond.allowed:
                    continue
                if cond.size_limit and cond.size_limit != "없음":
                    if dog_size_rank > SIZE_ORDER.get(cond.size_limit, 4):
                        continue
                if cond.vaccination_required and vaccination_count < cond.vaccination_required:
                    continue
                if cond.neutered_required and not is_neutered:
                    continue

            results.append(_place_to_dict(place, cond))
            if len(results) >= limit:
                break

        return results
    except SQLAlchemyError as e:
        logger.error("테마별 장소 조회 실패 (themes=%s): %s", themes, e)
        raise


def get_places_by_bbox(
    session: Session,
    min_lat: float,
    max_lat: float,
    min_lon: float,
    max_lon: float,
    themes: list[str],
) -> list[dict]:
    """바운딩 박스(위경도 범위) 내 장소 조회"""
    try:
        rows = (
            session.query(Place, PlaceCondition)
            .outerjoin(PlaceCondition, Place.place_id == PlaceCondition.place_id)
            .filter(Place.category.in_(themes))
            .filter(Place.lat.between(min_lat, max_lat))
            .filter(Place.lon.between(min_lon, max_lon))
            .all()
        )
        return [_place_to_dict(p, c) for p, c in rows]
    except SQLAlchemyError as e:
        logger.error("bbox 장소 조회 실패: %s", e)
        raise


def get_indoor_places(
    session: Session,
    themes: list[str],
    dog_size: str,
    vaccination_count: int,
    is_neutered: bool,
    limit: int = 20,
) -> list[dict]:
    """실내(indoor=True) 반려견 동반 가능 장소 조회 (날씨 나쁜 날 대안 검색용)"""
    try:
        dog_size_rank = SIZE_ORDER.get(dog_size, 1)

        rows = (
            session.query(Place, PlaceCondition)
            .join(PlaceCondition, Place.place_id == PlaceCondition.place_id)
            .filter(Place.category.in_(themes))
            .filter(PlaceCondition.indoor.is_(True))
            .filter(PlaceCondition.allowed.is_(True))
            .all()
        )

        results = []
        for place, cond in rows:
            if cond.size_limit and cond.size_limit != "없음":
                if dog_size_rank > SIZE_ORDER.get(cond.size_limit, 4):
                    continue
            if cond.vaccination_required and vaccination_count < cond.vaccination_required:
                continue
            if cond.neutered_required and not is_neutered:
                continue
            results.append(_place_to_dict(place, cond))
            if len(results) >= limit:
                break

        return results
    except SQLAlchemyError as e:
        logger.error("실내 장소 조회 실패 (themes=%s): %s", themes, e)
        raise


def get_places_by_ids(session: Session, place_ids: list[int]) -> dict[int, dict]:
    """place_id 목록으로 장소 정보를 {place_id: dict} 형태로 반환"""
    if not place_ids:
        return {}
    try:
        rows = (
            session.query(Place, PlaceCondition)
            .outerjoin(PlaceCondition, Place.place_id == PlaceCondition.place_id)
            .filter(Place.place_id.in_(place_ids))
            .all()
        )
        return {place.place_id: _place_to_dict(place, cond) for place, cond in rows}
    except SQLAlchemyError as e:
        logger.error("장소 ID 목록 조회 실패 (place_ids=%s): %s", place_ids, e)
        raise


def semantic_search_places(
    session: Session,
    query_embedding: list[float],
    themes: list[str],
    top_k: int = 20,
) -> list[dict]:
    """pgvector 코사인 유사도 기반 장소 검색"""
    try:
        rows = (
            session.query(Place, PlaceCondition)
            .outerjoin(PlaceCondition, Place.place_id == PlaceCondition.place_id)
            .filter(Place.category.in_(themes))
            .filter(Place.embedding.isnot(None))
            .order_by(Place.embedding.cosine_distance(query_embedding))
            .limit(top_k)
            .all()
        )
        return [_place_to_dict(p, c) for p, c in rows]
    except SQLAlchemyError as e:
        logger.error("시맨틱 검색 실패 (pgvector): %s", e)
        raise


def need_update(session: Session) -> bool:
    """places 데이터가 없거나 30일 이상 지났으면 True"""
    try:
        oldest = session.query(func.min(Place.updated_at)).scalar()
        if oldest is None:
            return True
        # DB 값이 timezone-naive일 수 있으므로 UTC로 통일
        if oldest.tzinfo is None:
            oldest = oldest.replace(tzinfo=datetime.timezone.utc)
        now = datetime.datetime.now(datetime.timezone.utc)
        return (now - oldest).days >= 30
    except SQLAlchemyError as e:
        logger.error("업데이트 필요 여부 확인 실패: %s", e)
        raise


# ──────────────────────────────────────────────
# UPDATE
# ──────────────────────────────────────────────

def update_place(session: Session, place: Place, data: dict) -> Place:
    """장소 정보 수정"""
    try:
        for k, v in data.items():
            setattr(place, k, v)
        place.updated_at = datetime.datetime.now(datetime.timezone.utc)
        session.flush()
        return place
    except SQLAlchemyError as e:
        logger.error("장소 수정 실패 (place_id=%s): %s", place.place_id, e)
        raise


# ──────────────────────────────────────────────
# DELETE
# ──────────────────────────────────────────────

def delete_place(session: Session, place: Place) -> None:
    """장소 삭제"""
    try:
        session.delete(place)
        session.flush()
    except SQLAlchemyError as e:
        logger.error("장소 삭제 실패 (place_id=%s): %s", place.place_id, e)
        raise


# ──────────────────────────────────────────────
# 내부 헬퍼
# ──────────────────────────────────────────────

def _place_to_dict(place: Place, cond: Optional[PlaceCondition]) -> dict:
    d = {
        "place_id": place.place_id,
        "place_name": place.place_name,
        "address": place.address,
        "category": place.category,
        "lat": place.lat,
        "lon": place.lon,
        "phone": place.phone,
        "opening_hours": place.opening_hours,
        "image_url": place.image_url,
        "rating": place.rating,
        "parking_available": place.parking_available,
    }
    if cond:
        d["conditions"] = {
            "allowed": cond.allowed,
            "indoor": cond.indoor,
            "terrace_only": cond.terrace_only,
            "carrier_required": cond.carrier_required,
            "leash_required": cond.leash_required,
            "size_limit": cond.size_limit,
            "weight_limit": cond.weight_limit,
            "vaccination_required": cond.vaccination_required,
            "neutered_required": cond.neutered_required,
            "dog_count_limit": cond.dog_count_limit,
        }
    return d
