"""
CSV 소스 적재

소스 1: KC_PET CSV (2023)       — 구조화된 조건 데이터 + 좌표 포함
소스 2: 대전관광공사 CSV (2025)  — 최신 카페/음식점/공원 + 카카오 지오코딩
"""
import csv
import hashlib
import logging
import time
from pathlib import Path

from sqlalchemy.orm import Session

from db.place_repository import create_place, get_place_by_source_id
from db.place_condition_repository import (
    create_place_condition, get_place_condition, update_place_condition,
)
from scripts.condition_parser import (
    parse_size_limit, parse_leash, parse_carrier,
)
from scripts.geocoder import geocode

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
KC_PET_CSV  = BASE_DIR / "data" / "KC_PET_ACP_CTLSTT_LC_DATA_2023.csv"
DAEJEON_CSV = BASE_DIR / "data" / "대전관광공사_대전 반려동물 동반 시설 안내_20250711.csv"

# KC_PET CTGRY_THREE_NM → places.category
KC_CATEGORY_MAP = {
    "여행지":   "관광지",
    "카페":     "카페",
    "박물관":   "문화시설",
    "미술관":   "문화시설",
    "문예회관": "문화시설",
}

# 대전관광공사 사업유형 → places.category
DJ_CATEGORY_MAP = {
    "동반카페":                             "카페",
    "전문 카페":                            "카페",
    "동반음식점":                           "맛집",
    "동반공원(광장)":                        "관광지",
    "여가 인프라(산책길, 편의시설, 놀이터)":   "관광지",
    "숙박시설":                             "숙박",
}


def _save_condition(session: Session, place_id: int, cond_data: dict) -> None:
    """조건 CREATE or UPDATE"""
    try:
        existing = get_place_condition(session, place_id)
        if existing:
            update_place_condition(session, existing, cond_data)
        else:
            create_place_condition(session, place_id, cond_data)
    except Exception as e:
        logger.error("CSV 조건 저장 실패 (place_id=%d): %s", place_id, e)
        raise


# ──────────────────────────────────────────────────────────
# KC_PET CSV
# ──────────────────────────────────────────────────────────

def load_kc_pet_csv(session: Session) -> list[tuple[int, str]]:
    """KC_PET CSV → places + place_conditions 적재. 임베딩용 (id, text) 반환."""
    if not KC_PET_CSV.exists():
        logger.warning(f"KC_PET CSV 없음: {KC_PET_CSV}")
        return []

    to_embed = []
    try:
        with open(KC_PET_CSV, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                try:
                    if row["CTPRVN_NM"] != "대전광역시":
                        continue

                    cat = KC_CATEGORY_MAP.get(row["CTGRY_THREE_NM"])
                    if not cat:
                        continue

                    lat = float(row["LC_LA"] or 0)
                    lon = float(row["LC_LO"] or 0)
                    if not lat or not lon:
                        continue

                    source_id = "kc_" + hashlib.md5(
                        (row["FCLTY_NM"] + row["RDNMADR_NM"]).encode()
                    ).hexdigest()[:12]

                    existing = get_place_by_source_id(session, source_id)
                    if existing:
                        to_embed.append((existing.place_id, f"{cat} {existing.place_name} {existing.address}"))
                        continue

                    place = create_place(session, {
                        "place_name":        row["FCLTY_NM"].strip(),
                        "address":           row["RDNMADR_NM"].strip(),
                        "category":          cat,
                        "lat":               lat,
                        "lon":               lon,
                        "source_id":         source_id,
                        "phone":             row.get("TEL_NO", "").strip(),
                        "opening_hours":     row.get("OPER_TIME", "").strip(),
                        "parking_available": row.get("PARKNG_POSBL_AT") == "Y",
                    })

                    lmt = row.get("PET_LMTT_MTR_CN", "")
                    _save_condition(session, place.place_id, {
                        "allowed":              row.get("PET_POSBL_AT") == "Y",
                        "indoor":               row.get("IN_PLACE_ACP_POSBL_AT") == "Y",
                        "terrace_only":         False,
                        "leash_required":       parse_leash(lmt),
                        "carrier_required":     parse_carrier(lmt),
                        "size_limit":           parse_size_limit(row.get("ENTRN_POSBL_PET_SIZE_VALUE", "")),
                        "neutered_required":    False,
                        "vaccination_required": 0,
                        "raw_text":             lmt,
                    })

                    to_embed.append((place.place_id, f"{cat} {place.place_name} {place.address}"))
                except Exception as row_err:
                    logger.warning("KC_PET CSV 행 스킵 (파싱 오류): %s", row_err)
                    continue
    except UnicodeDecodeError:
        logger.error("KC_PET CSV 인코딩 오류 (utf-8-sig 기대)")
    except Exception as e:
        logger.error("KC_PET CSV 로드 실패: %s", e)

    logger.info(f"[KC_PET CSV] {len(to_embed)}개 적재")
    return to_embed


# ──────────────────────────────────────────────────────────
# 대전관광공사 CSV
# ──────────────────────────────────────────────────────────

def load_daejeon_csv(session: Session) -> list[tuple[int, str]]:
    """대전관광공사 CSV → places + place_conditions 적재."""
    if not DAEJEON_CSV.exists():
        logger.warning(f"대전관광공사 CSV 없음: {DAEJEON_CSV}")
        return []

    to_embed = []
    try:
        with open(DAEJEON_CSV, encoding="euc-kr") as f:
            for row in csv.DictReader(f):
                try:
                    cat = DJ_CATEGORY_MAP.get(row["사업유형"])
                    if not cat:
                        continue

                    name      = row["업체명"].strip()
                    gu        = row.get("지역", "").strip()
                    addr_part = row["주소"].strip()
                    full_addr = f"대전광역시 {gu} {addr_part}" if gu else f"대전광역시 {addr_part}"

                    source_id = "dj_" + hashlib.md5(
                        (name + full_addr).encode()
                    ).hexdigest()[:12]

                    # 이미 있으면 지오코딩 스킵
                    existing = get_place_by_source_id(session, source_id)
                    if existing:
                        to_embed.append((existing.place_id, f"{cat} {name} {full_addr}"))
                        continue

                    coords = geocode(full_addr)
                    if not coords:
                        logger.warning(f"좌표 없음 스킵: {name} ({full_addr})")
                        continue

                    lat, lon = coords
                    time.sleep(0.05)  # 카카오 API 레이트리밋

                    place = create_place(session, {
                        "place_name":        name,
                        "address":           full_addr,
                        "category":          cat,
                        "lat":               lat,
                        "lon":               lon,
                        "source_id":         source_id,
                        "phone":             "",
                        "opening_hours":     "",
                        "parking_available": None,
                    })

                    _save_condition(session, place.place_id, {
                        "allowed":              True,
                        "indoor":               cat == "맛집",
                        "terrace_only":         False,
                        "leash_required":       True,
                        "carrier_required":     False,
                        "size_limit":           "없음",
                        "neutered_required":    False,
                        "vaccination_required": 0,
                        "raw_text":             "",
                    })

                    to_embed.append((place.place_id, f"{cat} {name} {full_addr}"))
                except Exception as row_err:
                    logger.warning("대전관광공사 CSV 행 스킵 (오류): %s", row_err)
                    continue
    except UnicodeDecodeError:
        logger.error("대전관광공사 CSV 인코딩 오류 (euc-kr 기대)")
    except Exception as e:
        logger.error("대전관광공사 CSV 로드 실패: %s", e)

    logger.info(f"[대전관광공사 CSV] {len(to_embed)}개 적재")
    return to_embed
