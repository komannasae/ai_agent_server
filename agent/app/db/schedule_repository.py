import datetime
import logging
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from db.models import Schedule

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# CREATE
# ──────────────────────────────────────────────

def create_schedule(
    session: Session,
    user_id: int,
    title: str,
    start_date: datetime.date,
    end_date: datetime.date,
    companion: str,
    theme: list[str],
    user_message: str,
) -> int:
    """schedules 테이블에 저장 후 schedule_id 반환"""
    try:
        schedule = Schedule(
            user_id=user_id,
            title=title,
            start_date=start_date,
            end_date=end_date,
            companion=companion,
            theme=theme,
            user_message=user_message,
        )
        session.add(schedule)
        session.flush()
        return schedule.schedule_id
    except SQLAlchemyError as e:
        logger.error("일정 생성 실패 (user_id=%s): %s", user_id, e)
        raise


# ──────────────────────────────────────────────
# READ
# ──────────────────────────────────────────────

def get_schedule_by_id(session: Session, schedule_id: int) -> Optional[Schedule]:
    """schedule_id로 일정 단건 조회"""
    try:
        return session.query(Schedule).filter_by(schedule_id=schedule_id).first()
    except SQLAlchemyError as e:
        logger.error("일정 조회 실패 (schedule_id=%s): %s", schedule_id, e)
        raise


def get_schedules_by_user(session: Session, user_id: int) -> list[Schedule]:
    """user_id로 일정 목록 조회"""
    try:
        return (
            session.query(Schedule)
            .filter_by(user_id=user_id)
            .order_by(Schedule.created_at.desc())
            .all()
        )
    except SQLAlchemyError as e:
        logger.error("사용자 일정 목록 조회 실패 (user_id=%s): %s", user_id, e)
        raise


# ──────────────────────────────────────────────
# UPDATE
# ──────────────────────────────────────────────

def update_schedule(session: Session, schedule: Schedule, data: dict) -> Schedule:
    """일정 수정"""
    try:
        for k, v in data.items():
            setattr(schedule, k, v)
        session.flush()
        return schedule
    except SQLAlchemyError as e:
        logger.error("일정 수정 실패 (schedule_id=%s): %s", schedule.schedule_id, e)
        raise


# ──────────────────────────────────────────────
# DELETE
# ──────────────────────────────────────────────

def delete_schedule(session: Session, schedule: Schedule) -> None:
    """일정 삭제"""
    try:
        session.delete(schedule)
        session.flush()
    except SQLAlchemyError as e:
        logger.error("일정 삭제 실패 (schedule_id=%s): %s", schedule.schedule_id, e)
        raise
