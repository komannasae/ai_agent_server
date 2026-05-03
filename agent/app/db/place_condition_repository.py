import logging
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from db.models import PlaceCondition

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# CREATE
# ──────────────────────────────────────────────

def create_place_condition(session: Session, place_id: int, data: dict) -> PlaceCondition:
    """반려견 조건 생성"""
    try:
        cond = PlaceCondition(place_id=place_id, **data)
        session.add(cond)
        session.flush()
        return cond
    except SQLAlchemyError as e:
        logger.error("반려견 조건 생성 실패 (place_id=%s): %s", place_id, e)
        raise


# ──────────────────────────────────────────────
# READ
# ──────────────────────────────────────────────

def get_place_condition(session: Session, place_id: int) -> Optional[PlaceCondition]:
    """place_id로 반려견 조건 단건 조회"""
    try:
        return session.query(PlaceCondition).filter_by(place_id=place_id).first()
    except SQLAlchemyError as e:
        logger.error("반려견 조건 조회 실패 (place_id=%s): %s", place_id, e)
        raise


# ──────────────────────────────────────────────
# UPDATE
# ──────────────────────────────────────────────

def update_place_condition(session: Session, cond: PlaceCondition, data: dict) -> PlaceCondition:
    """반려견 조건 수정"""
    try:
        for k, v in data.items():
            setattr(cond, k, v)
        session.flush()
        return cond
    except SQLAlchemyError as e:
        logger.error("반려견 조건 수정 실패 (place_id=%s): %s", cond.place_id, e)
        raise


# ──────────────────────────────────────────────
# DELETE
# ──────────────────────────────────────────────

def delete_place_condition(session: Session, cond: PlaceCondition) -> None:
    """반려견 조건 삭제"""
    try:
        session.delete(cond)
        session.flush()
    except SQLAlchemyError as e:
        logger.error("반려견 조건 삭제 실패 (place_id=%s): %s", cond.place_id, e)
        raise
