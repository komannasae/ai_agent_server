from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from pgvector.sqlalchemy import Vector
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import os
import uuid

load_dotenv()

# ============================
# DB 연결
# ============================
DATABASE_URL = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

engine  = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)


# ============================
# 임베딩 모델
# ============================
embedder = SentenceTransformer("jhgan/ko-sroberta-multitask")

def get_embedding(text: str) -> list[float]:
    return embedder.encode(text).tolist()


# ============================
# 테이블 초기화
# ============================
def init_db():
    with engine.connect() as conn:
        # pgvector 확장 활성화
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        # users
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                user_name    TEXT NOT NULL UNIQUE,
                password    TEXT NOT NULL,
                embedding   vector(768),
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # dogs
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dogs (
                id                  TEXT PRIMARY KEY,
                user_id             TEXT NOT NULL,
                dog_name            TEXT NOT NULL,
                size                TEXT NOT NULL,
                is_neutered         BOOLEAN NOT NULL,
                vaccination_count   INTEGER NOT NULL,
                embedding           vector(768),
                created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # trips
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS trips (
                id          TEXT PRIMARY KEY,
                user_id     TEXT NOT NULL,
                title       TEXT NOT NULL,
                destination TEXT NOT NULL,
                start_date  TEXT NOT NULL,
                end_date    TEXT NOT NULL,
                status      TEXT DEFAULT 'planning',
                embedding   vector(768),
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # schedules
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS schedules (
                id              TEXT PRIMARY KEY,
                trip_id         TEXT NOT NULL,
                schedule_date   TEXT NOT NULL,
                order_index     INTEGER NOT NULL,
                place_name      TEXT NOT NULL,
                memo            TEXT DEFAULT '',
                embedding       vector(768),
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # travel_places
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS travel_places (
                id              TEXT PRIMARY KEY,
                name            TEXT NOT NULL,
                description     TEXT NOT NULL,
                address         TEXT,
                dog_size        TEXT,
                is_pet_friendly BOOLEAN DEFAULT TRUE,
                embedding       vector(768),
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # chat_history
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id          TEXT PRIMARY KEY,
                user_id     TEXT NOT NULL,
                trip_id     TEXT NOT NULL,
                message     TEXT NOT NULL,
                role        TEXT NOT NULL,
                embedding   vector(768),
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # hospitals
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS hospitals (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                description TEXT NOT NULL,
                address     TEXT,
                phone       TEXT,
                embedding   vector(768),
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        # reviews
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS reviews (
                id          TEXT PRIMARY KEY,
                user_id     TEXT NOT NULL,
                content     TEXT NOT NULL,
                rating      FLOAT NOT NULL,
                image_path  TEXT,
                embedding   vector(768),
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        conn.commit()
    print("DB 테이블 초기화 완료")

# ============================
# 유저
# ============================
def save_user(user_id: str, name: str, user_name: str, hashed_pw: str):
    embedding = get_embedding(f"{name} {user_name}")
    with Session() as sess:
        sess.execute(text("""
            INSERT INTO users (id, name, user_name, password, embedding)
            VALUES (:id, :name, :user_name, :password, :embedding)
            ON CONFLICT (id) DO UPDATE
            SET name=:name, user_name=:user_name, password=:password, embedding=:embedding
        """), {"id": user_id, "name": name, "user_name": user_name,
               "password": hashed_pw, "embedding": embedding})
        sess.commit()

def get_user_by_username(user_name: str) -> dict | None:
    with Session() as sess:
        row = sess.execute(
            text("SELECT * FROM users WHERE user_name=:user_name"),
            {"user_name": user_name}
        ).mappings().fetchone()
    return dict(row) if row else None

def get_user_by_id(user_id: str) -> dict | None:
    with Session() as sess:
        row = sess.execute(
            text("SELECT * FROM users WHERE id=:id"),
            {"id": user_id}
        ).mappings().fetchone()
    return dict(row) if row else None


# ============================
# 강아지
# ============================
def save_dog(dog_id: str, user_id: str, dog_name: str, size: str,
             is_neutered: bool, vaccination_count: int):
    embedding = get_embedding(f"{dog_name} {size}")
    with Session() as sess:
        sess.execute(text("""
            INSERT INTO dogs (id, user_id, dog_name, size, is_neutered, vaccination_count, embedding)
            VALUES (:id, :user_id, :dog_name, :size, :is_neutered, :vaccination_count, :embedding)
            ON CONFLICT (id) DO UPDATE
            SET dog_name=:dog_name, size=:size, is_neutered=:is_neutered,
                vaccination_count=:vaccination_count, embedding=:embedding
        """), {"id": dog_id, "user_id": user_id, "dog_name": dog_name,
               "size": size, "is_neutered": is_neutered,
               "vaccination_count": vaccination_count, "embedding": embedding})
        sess.commit()

def get_dogs_by_user(user_id: str) -> list:
    with Session() as sess:
        rows = sess.execute(
            text("SELECT * FROM dogs WHERE user_id=:user_id"),
            {"user_id": user_id}
        ).mappings().fetchall()
    return [dict(r) for r in rows]


# ============================
# 여행
# ============================
def save_trip(trip_id: str, user_id: str, title: str, destination: str,
              start_date: str, end_date: str):
    embedding = get_embedding(f"{title} {destination}")
    with Session() as sess:
        sess.execute(text("""
            INSERT INTO trips (id, user_id, title, destination, start_date, end_date, embedding)
            VALUES (:id, :user_id, :title, :destination, :start_date, :end_date, :embedding)
            ON CONFLICT (id) DO UPDATE
            SET title=:title, destination=:destination,
                start_date=:start_date, end_date=:end_date, embedding=:embedding
        """), {"id": trip_id, "user_id": user_id, "title": title,
               "destination": destination, "start_date": start_date,
               "end_date": end_date, "embedding": embedding})
        sess.commit()

def get_trips_by_user(user_id: str) -> list:
    with Session() as sess:
        rows = sess.execute(
            text("SELECT * FROM trips WHERE user_id=:user_id ORDER BY created_at DESC"),
            {"user_id": user_id}
        ).mappings().fetchall()
    return [dict(r) for r in rows]


# ============================
# 스케줄
# ============================
def save_schedule(schedule_id: str, trip_id: str, schedule_date: str,
                  order_index: int, place_name: str, memo: str = ""):
    embedding = get_embedding(f"{place_name} {memo}")
    with Session() as sess:
        sess.execute(text("""
            INSERT INTO schedules (id, trip_id, schedule_date, order_index, place_name, memo, embedding)
            VALUES (:id, :trip_id, :schedule_date, :order_index, :place_name, :memo, :embedding)
            ON CONFLICT (id) DO UPDATE
            SET schedule_date=:schedule_date, order_index=:order_index,
                place_name=:place_name, memo=:memo, embedding=:embedding
        """), {"id": schedule_id, "trip_id": trip_id, "schedule_date": schedule_date,
               "order_index": order_index, "place_name": place_name,
               "memo": memo, "embedding": embedding})
        sess.commit()

def get_schedules_by_trip(trip_id: str, schedule_date: str = None) -> list:
    with Session() as sess:
        if schedule_date:
            rows = sess.execute(
                text("SELECT * FROM schedules WHERE trip_id=:trip_id AND schedule_date=:date ORDER BY order_index"),
                {"trip_id": trip_id, "date": schedule_date}
            ).mappings().fetchall()
        else:
            rows = sess.execute(
                text("SELECT * FROM schedules WHERE trip_id=:trip_id ORDER BY order_index"),
                {"trip_id": trip_id}
            ).mappings().fetchall()
    return [dict(r) for r in rows]


# ============================
# 여행지 벡터 검색
# ============================
def save_travel_place(place_id: str, name: str, description: str, metadata: dict):
    embedding = get_embedding(f"{name} {description}")
    with Session() as sess:
        sess.execute(text("""
            INSERT INTO travel_places (id, name, description, address, dog_size, is_pet_friendly, embedding)
            VALUES (:id, :name, :description, :address, :dog_size, :is_pet_friendly, :embedding)
            ON CONFLICT (id) DO UPDATE
            SET name=:name, description=:description, embedding=:embedding
        """), {"id": place_id, "name": name, "description": description,
               "address": metadata.get("address", ""),
               "dog_size": metadata.get("dog_size", "전체"),
               "is_pet_friendly": metadata.get("is_pet_friendly", True),
               "embedding": embedding})
        sess.commit()

def search_travel_places(query: str, dog_size: str = None, n_results: int = 5) -> list:
    embedding = get_embedding(query)
    with Session() as sess:
        if dog_size:
            rows = sess.execute(text("""
                SELECT *, 1 - (embedding <=> :embedding) AS score
                FROM travel_places
                WHERE dog_size IN (:dog_size, '전체')
                ORDER BY embedding <=> :embedding
                LIMIT :n
            """), {"embedding": embedding, "dog_size": dog_size, "n": n_results}).mappings().fetchall()
        else:
            rows = sess.execute(text("""
                SELECT *, 1 - (embedding <=> :embedding) AS score
                FROM travel_places
                ORDER BY embedding <=> :embedding
                LIMIT :n
            """), {"embedding": embedding, "n": n_results}).mappings().fetchall()
    return [dict(r) for r in rows]


# ============================
# 채팅 벡터 검색
# ============================
def save_chat_message(message_id: str, message: str, metadata: dict):
    embedding = get_embedding(message)
    with Session() as sess:
        sess.execute(text("""
            INSERT INTO chat_history (id, user_id, trip_id, message, role, embedding)
            VALUES (:id, :user_id, :trip_id, :message, :role, :embedding)
            ON CONFLICT (id) DO NOTHING
        """), {"id": message_id,
               "user_id": metadata.get("user_id", ""),
               "trip_id": metadata.get("trip_id", ""),
               "message": message,
               "role": metadata.get("role", "user"),
               "embedding": embedding})
        sess.commit()

def search_similar_chats(query: str, trip_id: str, n_results: int = 5) -> list:
    embedding = get_embedding(query)
    with Session() as sess:
        rows = sess.execute(text("""
            SELECT *, 1 - (embedding <=> :embedding) AS score
            FROM chat_history
            WHERE trip_id=:trip_id
            ORDER BY embedding <=> :embedding
            LIMIT :n
        """), {"embedding": embedding, "trip_id": trip_id, "n": n_results}).mappings().fetchall()
    return [dict(r) for r in rows]


# ============================
# 병원 벡터 검색
# ============================
def save_hospital(hospital_id: str, name: str, description: str, metadata: dict):
    embedding = get_embedding(f"{name} {description}")
    with Session() as sess:
        sess.execute(text("""
            INSERT INTO hospitals (id, name, description, address, phone, embedding)
            VALUES (:id, :name, :description, :address, :phone, :embedding)
            ON CONFLICT (id) DO UPDATE
            SET name=:name, description=:description, embedding=:embedding
        """), {"id": hospital_id, "name": name, "description": description,
               "address": metadata.get("address", ""),
               "phone": metadata.get("phone", ""),
               "embedding": embedding})
        sess.commit()

def search_hospitals(query: str, n_results: int = 5) -> list:
    embedding = get_embedding(query)
    with Session() as sess:
        rows = sess.execute(text("""
            SELECT *, 1 - (embedding <=> :embedding) AS score
            FROM hospitals
            ORDER BY embedding <=> :embedding
            LIMIT :n
        """), {"embedding": embedding, "n": n_results}).mappings().fetchall()
    return [dict(r) for r in rows]


# ============================
# 리뷰 (수정 중)
# ============================
REVIEW_IMAGE_DIR = "uploads/reviews"
os.makedirs(REVIEW_IMAGE_DIR, exist_ok=True)


def save_review(user_id: str, content: str, rating: float,
                image_path: str = None) -> dict:
    review_id = str(uuid.uuid4())
    embedding = get_embedding(content)
    with Session() as sess:
        sess.execute(text("""
                          INSERT INTO reviews (id, user_id, content, rating, image_path, embedding)
                          VALUES (:id, :user_id, :content, :rating, :image_path, :embedding)
                          """), {"id": review_id, "user_id": user_id, "content": content,
                                 "rating": rating, "image_path": image_path, "embedding": embedding})
        sess.commit()
    return get_review_by_id(review_id)



def get_review_by_id(review_id: str) -> dict | None:
    with Session() as sess:
        row = sess.execute(
            text("SELECT * FROM reviews WHERE id=:id"),
            {"id": review_id}
        ).mappings().fetchone()
    return dict(row) if row else None



def get_reviews(user_id: str = None, skip: int = 0, limit: int = 20) -> list:
    with Session() as sess:
        if user_id:
            rows = sess.execute(text("""
                                     SELECT *
                                     FROM reviews
                                     WHERE user_id = :user_id
                                     ORDER BY created_at DESC LIMIT :limit
                                     OFFSET :skip
                                     """), {"user_id": user_id, "limit": limit, "skip": skip}).mappings().fetchall()
        else:
            rows = sess.execute(text("""
                                     SELECT *
                                     FROM reviews
                                     ORDER BY created_at DESC LIMIT :limit
                                     OFFSET :skip
                                     """), {"limit": limit, "skip": skip}).mappings().fetchall()
    return [dict(r) for r in rows]


def delete_review(review_id: str) -> bool:
    row = get_review_by_id(review_id)
    if not row:
        return False
    if row.get("image_path") and os.path.exists(row["image_path"]):
        os.remove(row["image_path"])
    with Session() as sess:
        sess.execute(text("DELETE FROM reviews WHERE id=:id"), {"id": review_id})
        sess.commit()

    return True