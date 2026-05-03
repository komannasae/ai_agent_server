"""
한국관광공사 반려동물 API 적재

petTourSyncList2  — 반려동물 동반 장소 목록
detailPetTour2    — 반려동물 동반 조건 상세
"""
import logging
import time

import requests
from sqlalchemy.orm import Session

from config import TOURISM_API_KEY, TOURISM_BASE_URL
from db.place_repository import create_place, get_place_by_source_id, update_place
from db.place_condition_repository import (
    create_place_condition, get_place_condition, update_place_condition,
)
from scripts.condition_parser import (
    parse_size_limit, parse_leash, parse_carrier, parse_vaccination,
)

logger = logging.getLogger(__name__)

# 관광공사 contentTypeId → places.category
API_CATEGORY_MAP = {
    "12": "관광지",
    "14": "문화시설",
    "32": "숙박",
    "39": "카페",   # API 데이터상 음식점이지만 수집된 2건이 모두 카페
}


# ──────────────────────────────────────────────────────────
# 내부 헬퍼
# ──────────────────────────────────────────────────────────

def _api_get(endpoint: str, **params) -> dict:
    params.update({
        "serviceKey": TOURISM_API_KEY,
        "MobileOS":   "ETC",
        "MobileApp":  "PetTravelAgent",
        "_type":      "json",
    })
    try:
        r = requests.get(f"{TOURISM_BASE_URL}/{endpoint}", params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        logger.error("관광공사 API 호출 실패 (%s): %s", endpoint, e)
        raise


def _fetch_all_pages(filter_key: str, filter_val: str) -> list[dict]:
    """페이지네이션을 처리해 전체 항목 반환"""
    items, page = [], 1
    while True:
        try:
            resp = _api_get(
                "petTourSyncList2",
                numOfRows=100, pageNo=page,
                **{filter_key: filter_val},
            )
            body = resp.get("response", {}).get("body", {})

            raw   = body.get("items") or {}
            batch = raw.get("item", [])
            if isinstance(batch, dict):
                batch = [batch]
            if not batch:
                break

            items.extend(batch)
            if page * 100 >= int(body.get("totalCount", 0)):
                break
            page += 1
            time.sleep(0.1)
        except Exception as e:
            logger.error("페이지네이션 수집 중단 (%s=%s, page=%d): %s", filter_key, filter_val, page, e)
            break
    return items


def _save_place(session: Session, place_data: dict):
    """CREATE or UPDATE"""
    try:
        existing = get_place_by_source_id(session, place_data["source_id"])
        if existing:
            return update_place(session, existing, place_data)
        return create_place(session, place_data)
    except Exception as e:
        logger.error("장소 저장 실패 (%s): %s", place_data.get("place_name"), e)
        raise


def _save_condition(session: Session, place_id: int, cond_data: dict) -> None:
    """CREATE or UPDATE"""
    try:
        existing = get_place_condition(session, place_id)
        if existing:
            update_place_condition(session, existing, cond_data)
        else:
            create_place_condition(session, place_id, cond_data)
    except Exception as e:
        logger.error("반려견 조건 저장 실패 (place_id=%d): %s", place_id, e)
        raise


# ──────────────────────────────────────────────────────────
# 메인 로더
# ──────────────────────────────────────────────────────────

def load_api_places(session: Session) -> list[tuple[int, str]]:
    """관광공사 API → 관광지/문화시설/숙박/카페 적재. 임베딩용 (id, text) 반환."""
    to_embed = []

    # areaCode + lDongRegnCd 두 필터 합집합으로 대전 전체 커버
    seen_cids: set[str] = set()
    all_items: list[dict] = []
    for fk, fv in [("areaCode", "3"), ("lDongRegnCd", "30")]:
        for item in _fetch_all_pages(fk, fv):
            cid = str(item.get("contentid", ""))
            if cid not in seen_cids:
                seen_cids.add(cid)
                all_items.append(item)
        time.sleep(0.3)

    for item in all_items:
        try:
            cat = API_CATEGORY_MAP.get(item.get("contenttypeid", ""))
            if not cat:
                continue

            name      = item.get("title", "").strip()
            addr      = item.get("addr1", "").strip()
            source_id = f"api_{item.get('contentid', '')}"

            lat = float(item.get("mapy") or 0)
            lon = float(item.get("mapx") or 0)
            if not lat or not lon:
                continue

            place = _save_place(session, {
                "place_name":        name,
                "address":           addr,
                "category":          cat,
                "lat":               lat,
                "lon":               lon,
                "source_id":         source_id,
                "phone":             item.get("tel", ""),
                "image_url":         item.get("firstimage", ""),
                "parking_available": None,
            })

            # 반려견 조건 상세 조회
            try:
                detail   = _api_get("detailPetTour2", contentId=item["contentid"])
                det_item = (
                    detail.get("response", {}).get("body", {})
                          .get("items", {}) or {}
                ).get("item")

                if det_item:
                    if isinstance(det_item, list):
                        det_item = det_item[0]
                    raw = " | ".join(filter(None, [
                        det_item.get("acmpyTypeCd", ""),
                        det_item.get("acmpyPsblCpam", ""),
                        det_item.get("acmpyNeedMtr", ""),
                        det_item.get("etcAcmpyInfo", ""),
                    ]))
                    _save_condition(session, place.place_id, {
                        "allowed":              True,
                        "indoor":               "실내" in raw,
                        "terrace_only":         False,
                        "leash_required":       parse_leash(raw),
                        "carrier_required":     parse_carrier(raw),
                        "size_limit":           parse_size_limit(raw),
                        "neutered_required":    "중성화" in raw,
                        "vaccination_required": parse_vaccination(raw),
                        "raw_text":             raw,
                    })
                time.sleep(0.05)
            except Exception as e:
                logger.warning(f"API 조건 조회 실패 ({name}): {e}")

            to_embed.append((place.place_id, f"{cat} {name} {addr}"))
        except Exception as e:
            logger.error(f"API 개별 장소 처리 실패 (contentid={item.get('contentid')}): {e}")
            continue

    logger.info(f"[관광공사 API] {len(to_embed)}개 적재")
    return to_embed
