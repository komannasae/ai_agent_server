from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import logging

from routers import auth, dog, trip, weather, notification
from ws.location import router as ws_router

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="🐶 대전 기반 반려견 동반 여행 추천 API")

# ============================
# CORS
# ============================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://10.0.2.2:8000",         # Android 에뮬레이터
        "http://127.0.0.1:8000",        # iOS 시뮬레이터
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ============================
# 전역 예외 핸들러
# ============================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc} | path: {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"detail": "서버 내부 오류가 발생했습니다."}
    )

# ============================
# 라우터 등록
# ============================
app.include_router(auth.router,         prefix="/auth",         tags=["사용자 인증"])
app.include_router(dog.router,          prefix="/dog",          tags=["강아지"])
app.include_router(trip.router,         prefix="/trip",         tags=["여행"])
app.include_router(weather.router,      prefix="/weather",      tags=[" 날씨"])
app.include_router(notification.router, prefix="/notification", tags=[" 알림"])
app.include_router(ws_router,                                   tags=[" WebSocket"])

# ============================
# 시작 / 종료
# ============================
@app.on_event("startup")
async def startup():
    logger.info("============================")
    logger.info("  강아지 여행 서버 시작")
    logger.info("============================")
    try:
        from Db import travel_collection, chat_collection, hospital_collection
        logger.info("ChromaDB 연결 완료")
        logger.info(f"   - travel_places : {travel_collection.count()}개")
        logger.info(f"   - chat_history  : {chat_collection.count()}개")
        logger.info(f"   - hospitals     : {hospital_collection.count()}개")
    except Exception as e:
        logger.error(f" ChromaDB 연결 실패: {e}")

@app.on_event("shutdown")
async def shutdown():
    logger.info(" 서버 종료")

# ============================
# 기본 / 헬스체크
# ============================
@app.get("/", tags=["서버"])
def root():
    return {"message": " 서버 정상 작동"}

@app.get("/health", tags=[" 서버"])
async def health_check():
    status = {"server": "ok", "chromadb": "unknown"}
    try:
        from Db import travel_collection
        travel_collection.count()
        status["chromadb"] = "ok"
    except Exception as e:
        status["chromadb"] = f"error: {str(e)}"

    overall = all(v == "ok" for v in status.values())
    return JSONResponse(
        status_code=200 if overall else 503,
        content={"status": "healthy" if overall else "unhealthy", "detail": status}
    )