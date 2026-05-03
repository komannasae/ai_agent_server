"""
대전 반려견 동반 장소 데이터 통합 적재

3개 소스를 순서대로 적재하고 임베딩을 생성한다.
30일 이내에 이미 적재된 데이터가 있으면 아무것도 하지 않는다.

실행: python scripts/load_places.py
"""
import logging

from db.connection import SessionLocal
from db.models import Place
from db.place_repository import need_update
from scripts.csv_parser import load_kc_pet_csv, load_daejeon_csv
from scripts.api_client import load_api_places
from scripts.embedder import update_embeddings

logger = logging.getLogger(__name__)


def load_places() -> None:
    """세 소스 통합 적재. 30일 미경과 시 스킵."""
    with SessionLocal() as session:
        try:
            if not need_update(session):
                logger.info("DB 최신 상태 — 업데이트 불필요")
                return
        except Exception as e:
            logger.error("업데이트 체크 실패: %s", e)
            return

        logger.info("=== 장소 데이터 통합 적재 시작 ===")
        all_embed: list[tuple[int, str]] = []

        # 각 소스별로 독립적인 트랜잭션/세이브포인트처럼 처리하여 하나 실패가 전체 중단시키지 않게 함
        for loader_name, loader_func in [
            ("KC_PET CSV", load_kc_pet_csv),
            ("대전관광공사 CSV", load_daejeon_csv),
            ("관광공사 API", load_api_places),
        ]:
            try:
                all_embed += loader_func(session)
                session.flush()
            except Exception as e:
                logger.error("%s 적재 실패 (건너뜀): %s", loader_name, e)
                session.rollback()  # 해당 소스의 실패만 롤백

        try:
            update_embeddings(session, all_embed)
            session.commit()
            total = session.query(Place).count()
            logger.info(f"=== 적재 완료: DB 총 {total}개 장소 ===")
        except Exception as e:
            logger.error("최종 저장 또는 임베딩 생성 실패: %s", e)
            session.rollback()
            raise


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    load_places()
