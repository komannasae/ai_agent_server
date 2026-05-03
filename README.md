# 🐶 Pet Travel Agent – 진행 상황 (Backend + Agent 연동)
## 📌 현재 목표

기존 구조:

Agent → 로컬 DB 조회</br>

변경 목표:

Agent → FastAPI 서버 API → Docker DB</br>
## ✅ 1단계 진행 완료
### 🔧 아키텍처 변경
변경 전 :</br>
agent → DB 직접 접근</br>
server → DB</br>
변경 후 :</br>
agent → server API 호출</br>
server → Docker PostgreSQL(DB)</br>
## 📁 주요 변경 사항
### 1️⃣ Server (FastAPI)
app/routers/place.py</br>
장소 조회 API 추가</br>
/internal/places/* 엔드포인트 구성</br>
POST /internal/places/search</br>
POST /internal/places/semantic-search</br>
POST /internal/places/by-ids</br>
POST /internal/places/nearby</br>
POST /internal/places/indoor</br>
### 2️⃣ Agent
#### DB 직접 접근 제거
agent/app/db → 사용 안함 (legacy)</br>
서버 API 호출 방식으로 변경</br>
agent → server_api_client.py → FastAPI</br>
#### 주요 수정 파일
agent/app/tools/place_tools.py</br>
agent/app/tools/schedule_tools.py</br>
agent/app/graph/nodes.py</br>
기존:</br>
db.query(...)</br>
변경:</br>
requests.post("/internal/places/...")</br>
### 3️⃣ 환경 변수 처리 수정
.env.example → .env로 변경 필요</br>
.env.example ❌ (읽히지 않음)</br>
.env ✅ (실제 실행용)</br>
config.py에서 환경변수 로드 수정</br>
load_dotenv(".env")</br>
##🚀 실행 방법
### 1. DB 실행
docker compose up -d db</br>
### 2. 서버 실행
uvicorn app.main:app --reload --port 8000</br>

#### Swagger: http://127.0.0.1:8000/docs
###3. Agent 실행
cd agent/app</br>
python main.py</br>
## 🧪 테스트 (Swagger)

### 임시 테스트 API 추가:

POST /plans/test-save</br>

→ OpenAI 없이 일정 저장 테스트 가능</br>

## ⚠️ 현재 이슈
### 1. OpenAI API
Error 429: insufficient_quota</br>

👉 원인:</br>

API 크레딧 없음</br>

👉 해결:</br>

OpenAI 결제 필요</br>
2. 장소 데이터 없음</br>
후보 장소 0개 수집</br>

👉 원인:</br>

places 테이블 비어있음</br>

👉 해결 예정:</br>

load_places 스크립트 실행 필요</br>
## 🧹 남아있는 작업 (다음 단계)
## 🔜 2단계
장소 적재 로직 server로 이동</br>
agent/app/scripts/*</br>
→ server로 이전</br>

### 대상 파일:

load_places.py</br>
api_client.py</br>
csv_parser.py</br>
geocoder.py</br>
condition_parser.py</br>
embedder.py (일부)</br>
## 🔜 3단계
Agent 완전 Stateless화</br>
agent → LLM only</br>
server → 모든 데이터 처리</br>
## 🎯 핵심 정리
DB는 서버만 접근</br>
Agent는 API만 호출</br>
##💬 참고

## 현재 상태

### DB 연결 ✅
### Server API ✅
### Agent 연동 ✅
### 일정 저장 테스트 ✅
### OpenAI ❌ (크레딧 필요)
### 장소 데이터 ❌ (적재 필요)
