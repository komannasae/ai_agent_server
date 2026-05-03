import logging

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session

from config import DATABASE_URL

logger = logging.getLogger(__name__)

# 데이터 베이스 연결 및 설정
try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except SQLAlchemyError as e:
    logger.error("데이터베이스 엔진 생성 실패: %s", e)
    raise

#전체 테이블 관리가 쉽도록 만든 상속
class Base(DeclarativeBase):
    pass

def get_session() -> Session:
    """세션 생성. 실패 시 로깅 후 예외 전파."""
    try:
        return SessionLocal()
    except SQLAlchemyError as e:
        logger.error("데이터베이스 세션 생성 실패: %s", e)
        raise
