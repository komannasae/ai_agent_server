"""
sentence-transformers 기반 임베딩 생성

모델: jhgan/ko-sroberta-multitask (한국어 최적화, 768차원)
첫 호출 시 모델을 다운로드하고 이후에는 메모리에 캐싱한다.

주의:
- agent 추천 실행 경로에서는 get_embedding()만 사용한다.
- update_embeddings()는 과거 적재 스크립트 호환용이며, 실행 시에만 db.models를 lazy import한다.
"""
import logging
from typing import Any

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """모델 싱글턴 — 최초 호출 시 로드."""
    global _model
    if _model is None:
        try:
            logger.info("임베딩 모델 로드 중: jhgan/ko-sroberta-multitask")
            _model = SentenceTransformer("jhgan/ko-sroberta-multitask")
        except Exception as e:
            logger.error("임베딩 모델 로드 실패: %s", e)
            raise
    return _model


def get_embedding(text: str) -> list[float]:
    """단일 텍스트 임베딩 벡터 반환."""
    try:
        return _get_model().encode(text).tolist()
    except Exception as e:
        logger.error("텍스트 임베딩 생성 실패: %s", e)
        raise


def update_embeddings(session: Any, to_embed: list[tuple[int, str]]) -> None:
    """임베딩이 없는 장소만 배치 생성 후 Place.embedding 컬럼에 저장. 과거 적재 스크립트 호환용."""
    from db.models import Place  # legacy loader에서만 사용

    try:
        need = []
        for pid, txt in to_embed:
            place = session.get(Place, pid)
            if place and place.embedding is None:
                need.append((pid, txt))

        if not need:
            logger.info("임베딩 생성: 신규 항목 없음")
            return

        logger.info("임베딩 생성: %d개", len(need))
        model = _get_model()

        ids = [item[0] for item in need]
        texts = [item[1] for item in need]
        embeddings = model.encode(texts, batch_size=32, show_progress_bar=True)

        for pid, emb in zip(ids, embeddings):
            place = session.get(Place, pid)
            if place:
                place.embedding = emb.tolist()
    except Exception as e:
        logger.error("배치 임베딩 업데이트 실패: %s", e)
        raise
