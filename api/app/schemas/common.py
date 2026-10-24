from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, Optional, Union
from fastapi import HTTPException
from pydantic import BaseModel, Field


class ErrorPayload(BaseModel):
    code: str
    message: str
    fields: Dict[str, str] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorPayload


class HealthResponse(BaseModel):
    status: str = "ok"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AppError(HTTPException):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        fields: Optional[Dict[str, str]] = None
    ):
        super().__init__(status_code=status_code, detail=message)
        self.code = code
        self.fields = fields or {}


def format_datetime(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def format_score(score: Optional[Union[Decimal, float, int, str]]) -> Optional[str]:
    if score is None:
        return None
    try:
        return f"{Decimal(str(score)):.2f}"
    except Exception:
        return str(score)
