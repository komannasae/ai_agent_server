"""
반려견 동반 조건 텍스트 파싱 헬퍼

원본 텍스트(raw_text)에서 크기 제한, 목줄, 캐리어, 예방접종 정보를 추출한다.
"""
import re


def parse_size_limit(val: str) -> str:
    """반려견 크기 제한 텍스트 → "소형" | "중형" | "대형" | "없음" """
    val = val.strip()
    if not val or "모두" in val:
        return "없음"
    for sz in ["소형", "중형", "대형"]:
        if sz in val:
            return sz
    m = re.search(r"(\d+)\s*kg", val)
    if m:
        kg = int(m.group(1))
        if kg <= 7:
            return "소형"
        if kg <= 15:
            return "중형"
        return "대형"
    return "없음"


def parse_leash(val: str) -> bool:
    """목줄 필요 여부"""
    return "목줄" in val


def parse_carrier(val: str) -> bool:
    """이동장(캐리어/켄넬) 필요 여부"""
    return any(k in val for k in ["이동가방", "켄넬", "이동장", "캐리어"])


def parse_vaccination(val: str) -> int:
    """예방접종 차수 추출. 없으면 0."""
    m = re.search(r"(\d+)차\s*(?:이상\s*)?예방접종", val)
    return int(m.group(1)) if m else 0
