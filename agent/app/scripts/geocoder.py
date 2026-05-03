"""
카카오 지오코딩

주소 문자열을 위도·경도 좌표로 변환한다.
"""
import json
import logging
import urllib.parse
import urllib.request

from config import KAKAO_API_KEY

logger = logging.getLogger(__name__)


def geocode(address: str) -> tuple[float, float] | None:
    """주소 → (lat, lon).  변환 실패 시 None 반환."""
    try:
        qs = urllib.parse.urlencode({"query": address})
        url = f"https://dapi.kakao.com/v2/local/search/address.json?{qs}"
        req = urllib.request.Request(
            url, headers={"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            docs = json.loads(resp.read()).get("documents", [])
            if docs:
                return float(docs[0]["y"]), float(docs[0]["x"])
    except Exception as e:
        logger.warning(f"지오코딩 실패 ({address}): {e}")
    return None
