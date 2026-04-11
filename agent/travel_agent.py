# TODO: Claude / GPT API 연동
# from anthropic import Anthropic
# client = Anthropic(api_key="YOUR_API_KEY")

async def recommend_trip_agent(destination: str, dog_size: str, start_date: str, end_date: str) -> dict:
    # TODO: 벡터 DB에서 유사 여행지 검색 후 AI에 컨텍스트로 전달
    # 흐름: 벡터 검색 → 프롬프트 구성 → AI 응답 → 스케줄 파싱 → 반환
    return {
        "destination": destination,
        "dog_size":    dog_size,
        "recommend":   "AI 에이전트 구현 예정",    # TODO
        "schedule":    []
    }