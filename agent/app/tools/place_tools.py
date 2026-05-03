"""
장소 검색 함수

place_search_node에서 호출하는 순수 Python 함수.
이 파일은 더 이상 DB 세션을 받지 않는다.
Agent는 FastAPI 서버 API를 통해 장소 후보를 조회한다.
"""
import logging

from scripts.embedder import get_embedding
from scripts.server_api_client import (
    search_places as request_place_search,
    semantic_search_places as request_semantic_search,
)

logger = logging.getLogger(__name__)


def search_places(
    themes: list[str],
    dog_size: str,
    vaccination_count: int,
    is_neutered: bool,
    limit: int = 60,
) -> list[dict]:
    """테마 + 반려견 조건 필터로 후보 장소 조회. 실제 DB 조회는 server가 수행한다."""
    try:
        return request_place_search(
            themes=themes,
            dog_size=dog_size,
            vaccination_count=vaccination_count,
            is_neutered=is_neutered,
            limit=limit,
        )
    except Exception as e:
        logger.error("search_places 서버 API 호출 중 오류 발생: %s", e)
        return []


def semantic_search(
    user_message: str,
    themes: list[str],
    top_k: int = 20,
) -> list[dict]:
    """user_message 임베딩 생성 후, server API에 pgvector 검색을 요청한다."""
    try:
        embedding = get_embedding(user_message)
        return request_semantic_search(embedding, themes, top_k=top_k)
    except Exception as e:
        logger.error("semantic_search 서버 API 호출 중 오류 발생: %s", e)
        return []
