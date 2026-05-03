import logging
import os
from pathlib import Path
from dotenv import load_dotenv

CURRENT_DIR = Path(__file__).resolve().parent          # agent/app
AGENT_DIR = CURRENT_DIR.parent                         # agent
ROOT_DIR = AGENT_DIR.parent.parent                     # Capston

load_dotenv(ROOT_DIR / ".env", override=True)
load_dotenv(CURRENT_DIR / ".env", override=True)

logger = logging.getLogger(__name__)

# 환경변수 로드 (누락 시 경고 로그 출력, 빈 문자열로 초기화)
OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY") or ""
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")

TOURISM_API_KEY: str = os.environ.get("TOURISM_API_KEY") or ""
if not TOURISM_API_KEY:
    logger.warning("TOURISM_API_KEY 환경변수가 설정되지 않았습니다.")

KAKAO_API_KEY: str = os.environ.get("KAKAO_API_KEY") or ""
if not KAKAO_API_KEY:
    logger.warning("KAKAO_API_KEY 환경변수가 설정되지 않았습니다.")

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://pet_travel_user:pet_travel_pass@localhost:5432/pet_travel_db",
)


# agent가 DB에 직접 접근하지 않고 FastAPI 서버를 통해 장소 데이터를 조회한다.
SERVER_API_BASE_URL: str = os.getenv("SERVER_API_BASE_URL", "http://127.0.0.1:9000")

AREA_CODE = "3"  # 대전광역시
TOURISM_BASE_URL = "https://apis.data.go.kr/B551011/KorPetTourService2"

# 서비스에서 사용하는 장소 카테고리
ALLOWED_CATEGORIES: list[str] = ["관광지", "카페", "문화시설", "맛집", "숙박"]

# 반려견 크기 순위 (클수록 큰 개)
SIZE_ORDER: dict[str, int] = {"소형": 1, "중형": 2, "대형": 3, "맹견": 4}
