import chromadb
import uuid
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import os

load_dotenv()

# ============================
# ChromaDB 클라이언트
# ============================
chroma_client = chromadb.PersistentClient(
    path=os.getenv("CHROMA_PATH", "./chroma_db"),
    settings=Settings(anonymized_telemetry=False)
)

# ============================
# 컬렉션 전체 정의
# ============================
user_collection     = chroma_client.get_or_create_collection(name="users",         metadata={"hnsw:space": "cosine"})
dog_collection      = chroma_client.get_or_create_collection(name="dogs",           metadata={"hnsw:space": "cosine"})
trip_collection     = chroma_client.get_or_create_collection(name="trips",          metadata={"hnsw:space": "cosine"})
schedule_collection = chroma_client.get_or_create_collection(name="schedules",      metadata={"hnsw:space": "cosine"})
travel_collection   = chroma_client.get_or_create_collection(name="travel_places",  metadata={"hnsw:space": "cosine"})
chat_collection     = chroma_client.get_or_create_collection(name="chat_history",   metadata={"hnsw:space": "cosine"})
hospital_collection = chroma_client.get_or_create_collection(name="hospitals",      metadata={"hnsw:space": "cosine"})


# ============================
# 임베딩 모델
# ============================
embedder = SentenceTransformer("jhgan/ko-sroberta-multitask")

def get_embedding(text: str) -> list[float]:
    return embedder.encode(text).tolist()


# ============================
# 유저
# ============================
def save_user(user_id: str, name: str, username: str, hashed_pw: str) -> str:
    user_collection.upsert(
        ids=[user_id],
        embeddings=[get_embedding(f"{name} {username}")],
        documents=[username],
        metadatas=[{
            "name":     name,
            "username": username,
            "password": hashed_pw,
        }]
    )
    return user_id

def get_user_by_username(username: str) -> dict | None:
    results = user_collection.query(
        query_embeddings=[get_embedding(username)],
        n_results=10,
        include=["metadatas", "documents"]
    )
    for i, meta in enumerate(results["metadatas"][0]):
        if meta.get("username") == username:
            return {"id": results["ids"][0][i], **meta}
    return None

def get_user_by_id(user_id: str) -> dict | None:
    try:
        result = user_collection.get(ids=[user_id], include=["metadatas"])
        if result["ids"]:
            return {"id": user_id, **result["metadatas"][0]}
        return None
    except:
        return None


# ============================
# 강아지
# ============================
def save_dog(dog_id: str, user_id: str, dog_name: str, size: str, is_neutered: bool, vaccination_count: int) -> str:
    dog_collection.upsert(
        ids=[dog_id],
        embeddings=[get_embedding(f"{dog_name} {size}")],
        documents=[dog_name],
        metadatas=[{
            "user_id":           user_id,
            "dog_name":          dog_name,
            "size":              size,
            "is_neutered":       str(is_neutered),
            "vaccination_count": str(vaccination_count),
        }]
    )
    return dog_id

def get_dogs_by_user(user_id: str) -> list:
    results = dog_collection.get(
        where={"user_id": user_id},
        include=["metadatas"]
    )
    return [
        {"id": results["ids"][i], **results["metadatas"][i]}
        for i in range(len(results["ids"]))
    ]


# ============================
# 여행
# ============================
def save_trip(trip_id: str, user_id: str, title: str, destination: str, start_date: str, end_date: str) -> str:
    trip_collection.upsert(
        ids=[trip_id],
        embeddings=[get_embedding(f"{title} {destination}")],
        documents=[title],
        metadatas=[{
            "user_id":     user_id,
            "title":       title,
            "destination": destination,
            "start_date":  start_date,
            "end_date":    end_date,
            "status":      "planning",
        }]
    )
    return trip_id

def get_trips_by_user(user_id: str) -> list:
    results = trip_collection.get(
        where={"user_id": user_id},
        include=["metadatas"]
    )
    return [
        {"id": results["ids"][i], **results["metadatas"][i]}
        for i in range(len(results["ids"]))
    ]


# ============================
# 스케줄
# ============================
def save_schedule(schedule_id: str, trip_id: str, schedule_date: str, order_index: int, place_name: str, memo: str = "") -> str:
    schedule_collection.upsert(
        ids=[schedule_id],
        embeddings=[get_embedding(f"{place_name} {memo}")],
        documents=[place_name],
        metadatas=[{
            "trip_id":       trip_id,
            "schedule_date": schedule_date,
            "order_index":   str(order_index),
            "place_name":    place_name,
            "memo":          memo,
        }]
    )
    return schedule_id

def get_schedules_by_trip(trip_id: str, schedule_date: str = None) -> list:
    where = {"trip_id": trip_id}
    if schedule_date:
        where["schedule_date"] = schedule_date

    results = schedule_collection.get(
        where=where,
        include=["metadatas"]
    )
    items = [
        {"id": results["ids"][i], **results["metadatas"][i]}
        for i in range(len(results["ids"]))
    ]
    # order_index 기준 정렬
    return sorted(items, key=lambda x: int(x.get("order_index", 0)))


# ============================
# 여행지
# ============================
def save_travel_place(place_id: str, name: str, description: str, metadata: dict):
    travel_collection.upsert(
        ids=[place_id],
        embeddings=[get_embedding(f"{name} {description}")],
        documents=[description],
        metadatas=[{"name": name, **metadata}]
    )

def search_travel_places(query: str, dog_size: str = None, n_results: int = 5) -> list:
    where = {"dog_size": {"$in": [dog_size, "전체"]}} if dog_size else None
    results = travel_collection.query(
        query_embeddings=[get_embedding(query)],
        n_results=n_results,
        where=where,
        include=["documents", "metadatas", "distances"]
    )
    return [
        {
            "id":       results["ids"][0][i],
            "name":     results["metadatas"][0][i].get("name"),
            "document": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "score":    round(1 - results["distances"][0][i], 3)
        }
        for i in range(len(results["ids"][0]))
    ]


# ============================
# 채팅
# ============================
def save_chat_message(message_id: str, message: str, metadata: dict):
    chat_collection.upsert(
        ids=[message_id],
        embeddings=[get_embedding(message)],
        documents=[message],
        metadatas=[metadata]
    )

def search_similar_chats(query: str, trip_id: str, n_results: int = 5) -> list:
    results = chat_collection.query(
        query_embeddings=[get_embedding(query)],
        n_results=n_results,
        where={"trip_id": trip_id},
        include=["documents", "metadatas", "distances"]
    )
    return [
        {
            "message":  results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "score":    round(1 - results["distances"][0][i], 3)
        }
        for i in range(len(results["ids"][0]))
    ]


# ============================
# 병원
# ============================
def save_hospital(hospital_id: str, name: str, description: str, metadata: dict):
    hospital_collection.upsert(
        ids=[hospital_id],
        embeddings=[get_embedding(f"{name} {description}")],
        documents=[description],
        metadatas=[{"name": name, **metadata}]
    )

def search_hospitals(query: str, n_results: int = 5) -> list:
    results = hospital_collection.query(
        query_embeddings=[get_embedding(query)],
        n_results=n_results,
        include=["documents", "metadatas", "distances"]
    )
    return [
        {
            "name":     results["metadatas"][0][i].get("name"),
            "document": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "score":    round(1 - results["distances"][0][i], 3)
        }
        for i in range(len(results["ids"][0]))
    ]


def get_db():
    return None