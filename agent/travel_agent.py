# TODO: Claude / GPT API 연동
# from anthropic import Anthropic
# client = Anthropic(api_key="YOUR_API_KEY")

async def recommend_trip_agent(destination: str, dog_size: str, start_date: str, end_date: str) -> dict:
    # TODO: DB에서 여행지 검색 후 AI에 컨텍스트로 전달
    return {
        "destination": destination,
        "dog_size":    dog_size,
        "recommend":   "AI 에이전트 구현 예정",    # TODO
        "schedule":    []
    }