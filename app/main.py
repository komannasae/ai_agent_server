from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.connection import get_db_connection
from app.routers import auth, plan, place

app = FastAPI(
    title="대전 반려견 동반 여행 에이전트",
    description="LangGraph 기반 자율형 여행 일정 추천 API",
    version="0.1.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록 (plan.router 반드시 존재해야 함)
app.include_router(auth.router)
app.include_router(plan.router)
app.include_router(place.router)


# 기본 확인
@app.get("/")
async def root():
    return {"message": "API 서버 실행 중"}


# DB 연결 테스트
@app.get("/db-test")
def db_test():
    try:
        conn = get_db_connection()

        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public';
            """)
            tables = cur.fetchall()

        conn.close()

        return {
            "status": "success",
            "tables": [table[0] for table in tables]
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


# 헬스 체크
@app.get("/health")
async def health_check():
    return {"status": "ok"}