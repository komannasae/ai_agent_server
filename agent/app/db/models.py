import datetime
from sqlalchemy import Column, Integer, String, Boolean, Float, Text, DateTime, Date, ForeignKey, JSON
from pgvector.sqlalchemy import Vector
from db.connection import Base


class Place(Base):
    __tablename__ = "places"

    place_id = Column(Integer, primary_key=True, autoincrement=True)
    place_name = Column(String, nullable=False)
    address = Column(String)
    category = Column(String)
    lat = Column(Float)
    lon = Column(Float)
    source_id = Column(String, unique=True, nullable=False)
    phone = Column(String)
    opening_hours = Column(String)
    image_url = Column(String)
    rating = Column(Float)
    parking_available = Column(Boolean)
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))
    embedding = Column(Vector(768))


class PlaceCondition(Base):
    __tablename__ = "place_conditions"

    condition_id = Column(Integer, primary_key=True, autoincrement=True)
    place_id = Column(Integer, ForeignKey("places.place_id"), unique=True)
    allowed = Column(Boolean, default=True)
    indoor = Column(Boolean, default=False)
    terrace_only = Column(Boolean, default=False)
    carrier_required = Column(Boolean, default=False)
    leash_required = Column(Boolean, default=True)
    size_limit = Column(String, default="없음")
    weight_limit = Column(Float)
    vaccination_required = Column(Integer, default=0)
    neutered_required = Column(Boolean, default=False)
    dog_count_limit = Column(Integer)
    raw_text = Column(Text)


class Schedule(Base):
    __tablename__ = "schedules"

    schedule_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)  # users 테이블은 서버팀 관리
    title = Column(String)
    start_date = Column(Date)
    end_date = Column(Date)
    companion = Column(String)
    theme = Column(JSON)
    user_message = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))


class ScheduleItem(Base):
    __tablename__ = "schedule_items"

    item_id = Column(Integer, primary_key=True, autoincrement=True)
    schedule_id = Column(Integer, ForeignKey("schedules.schedule_id"))
    place_id = Column(Integer, ForeignKey("places.place_id"))
    day = Column(Integer)
    time_slot = Column(String)
    item_order = Column("order", Integer)  # "order"는 SQL 예약어 → Python 속성명은 item_order
    memo = Column(Text)
