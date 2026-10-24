from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from api.app.config import settings
from api.app.database import get_db
from api.app.services.remote_storage import remote_storage_enabled
from api.app.schemas.common import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def get_health():
    return HealthResponse(status="ok")


@router.get("/health/ready", response_model=HealthResponse)
def get_readiness(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database is unavailable") from exc
    if remote_storage_enabled() and (not settings.SUPABASE_URL or not settings.SUPABASE_SECRET_KEY):
        raise HTTPException(status_code=503, detail="Storage is not configured")
    return HealthResponse(status="ok")
