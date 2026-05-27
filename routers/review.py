from fastapi import APIRouter, File, Form, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Optional
from datetime import datetime
import shutil, uuid, os, logging

from Db import save_review, get_reviews, get_review_by_id, delete_review

logger = logging.getLogger(__name__)
router = APIRouter()

UPLOAD_DIR = "uploads/reviews"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _image_url(base_url: str, image_path: Optional[str]) -> Optional[str]:
    if not image_path:
        return None
    return f"{base_url}uploads/reviews/{os.path.basename(image_path)}"


def _to_dict(row: dict, base_url: str) -> dict:
    created = row["created_at"]
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "content": row["content"],
        "rating": row["rating"],
        "image_url": _image_url(base_url, row.get("image_path")),
        "created_at": created.isoformat() if isinstance(created, datetime) else str(created),
    }


# ── 리뷰 작성 ─────────────────────────────────────────────────────────
@router.post("")
async def create_review(
        request: Request,
        user_id: str = Form(...),
        content: str = Form(...),
        rating: float = Form(...),
        image: Optional[UploadFile] = File(None),
):
    if not (1 <= rating <= 5):
        raise HTTPException(status_code=422, detail="rating은 1~5 사이여야 합니다.")
    if len(content.strip()) < 5:
        raise HTTPException(status_code=422, detail="내용은 5자 이상이어야 합니다.")

    image_path = None
    if image and image.filename:
        ext = os.path.splitext(image.filename)[1]
        filename = f"{uuid.uuid4()}{ext}"
        image_path = os.path.join(UPLOAD_DIR, filename)
        with open(image_path, "wb") as f:
            shutil.copyfileobj(image.file, f)

    try:
        row = save_review(user_id=user_id, content=content,
                          rating=rating, image_path=image_path)
    except Exception as e:
        logger.error(f"리뷰 저장 실패: {e}")
        raise HTTPException(status_code=500, detail="리뷰 저장에 실패했습니다.")

    return JSONResponse(status_code=201, content=_to_dict(row, str(request.base_url)))


# ── 리뷰 목록 조회 ────────────────────────────────────────────────────
@router.get("")
def list_reviews(
        request: Request,
        user_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
):
    rows = get_reviews(user_id=user_id, skip=skip, limit=limit)
    return [_to_dict(r, str(request.base_url)) for r in rows]