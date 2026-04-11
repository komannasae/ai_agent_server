# pip install httpx beautifulsoup4
import httpx
from bs4 import BeautifulSoup

async def crawl_pet_places(keyword: str) -> list:
    # TODO: 네이버 블로그 / 카페 크롤링
    # 예: "제주도 강아지 동반 카페" 검색 결과 파싱
    results = []
    # async with httpx.AsyncClient() as client:
    #     res = await client.get(f"https://search.naver.com/search.naver?query={keyword}")
    #     soup = BeautifulSoup(res.text, "html.parser")
    #     ...파싱 로직...
    return results

