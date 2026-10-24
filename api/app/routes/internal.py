"""Authenticated endpoint for scheduled deadline processing."""

import hmac
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from api.app.config import settings
from api.app.database import get_db
from api.app.schemas.common import AppError
from api.app.services.deadline_service import run_deadline_tick

router = APIRouter(prefix="/internal", tags=["Internal"])


@router.get("/tick")
def deadline_tick(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    if not settings.CRON_SECRET:
        raise AppError(status_code=503, code="CRON_NOT_CONFIGURED", message="Tác vụ hạn chưa được cấu hình.")
    expected = f"Bearer {settings.CRON_SECRET}"
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise AppError(status_code=401, code="UNAUTHORIZED", message="Không có quyền chạy tác vụ hạn.")
    return run_deadline_tick(db, datetime.now(timezone.utc))
