import logging
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from db.models import ScheduleItem

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# CREATE
# ──────────────────────────────────────────────

def create_schedule_items(session: Session, schedule_id: int, items: list[dict]) -> None:
    """schedule_items 테이블에 저장"""
    try:
        for item in items:
            session.add(ScheduleItem(
                schedule_id=schedule_id,
                place_id=item.get("place_id"),
                day=item.get("day"),
                time_slot=item.get("time_slot"),
                item_order=item.get("order"),
                memo=item.get("memo"),
            ))
        session.flush()
    except (SQLAlchemyError, KeyError) as e:
        logger.error("일정 아이템 생성 실패 (schedule_id=%s): %s", schedule_id, e)
        raise


# ──────────────────────────────────────────────
# READ
# ──────────────────────────────────────────────

def get_schedule_items(session: Session, schedule_id: int) -> list[ScheduleItem]:
    """schedule_id로 일정 아이템 목록 조회"""
    try:
        return (
            session.query(ScheduleItem)
            .filter_by(schedule_id=schedule_id)
            .order_by(ScheduleItem.day, ScheduleItem.item_order)
            .all()
        )
    except SQLAlchemyError as e:
        logger.error("일정 아이템 목록 조회 실패 (schedule_id=%s): %s", schedule_id, e)
        raise


def get_schedule_item_by_id(session: Session, item_id: int) -> Optional[ScheduleItem]:
    """item_id로 일정 아이템 단건 조회"""
    try:
        return session.query(ScheduleItem).filter_by(item_id=item_id).first()
    except SQLAlchemyError as e:
        logger.error("일정 아이템 조회 실패 (item_id=%s): %s", item_id, e)
        raise


# ──────────────────────────────────────────────
# UPDATE
# ──────────────────────────────────────────────

def update_schedule_item(session: Session, item: ScheduleItem, data: dict) -> ScheduleItem:
    """일정 아이템 수정"""
    try:
        for k, v in data.items():
            setattr(item, k, v)
        session.flush()
        return item
    except SQLAlchemyError as e:
        logger.error("일정 아이템 수정 실패 (item_id=%s): %s", item.item_id, e)
        raise


# ──────────────────────────────────────────────
# DELETE
# ──────────────────────────────────────────────

def delete_schedule_items(session: Session, schedule_id: int) -> None:
    """schedule_id에 해당하는 아이템 전체 삭제"""
    try:
        session.query(ScheduleItem).filter_by(schedule_id=schedule_id).delete()
        session.flush()
    except SQLAlchemyError as e:
        logger.error("일정 아이템 삭제 실패 (schedule_id=%s): %s", schedule_id, e)
        raise
