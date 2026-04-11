from fastapi import APIRouter, HTTPException
import httpx

router = APIRouter()

KAKAO_API_KEY = "YOUR_KAKAO_REST_API_KEY"

@router.get("/search")
async def search_places(keyword: str, lat: float, lng: float):
    # TODO: 카카오 로컬 API
    async with httpx.AsyncClient() as client:
        res = await client.get(
            "https://dapi.kakao.com/v2/local/search/keyword.json",
            params={"query": keyword, "x": lng, "y": lat, "radius": 5000},
            headers={"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
        )
    if res.status_code != 200:
        raise HTTPException(status_code=502, detail="장소 검색 실패")
    return res.json()


@router.get("/hospital")
async def get_nearby_hospitals(lat: float, lng: float):
    # TODO: 공공데이터 동물병원 API 연동
    async with httpx.AsyncClient() as client:
        res = await client.get(
            "https://dapi.kakao.com/v2/local/search/keyword.json",
            params={"query": "동물병원", "x": lng, "y": lat, "radius": 3000},
            headers={"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
        )
    if res.status_code != 200:
        raise HTTPException(status_code=502, detail="병원 검색 실패")
    return res.json()