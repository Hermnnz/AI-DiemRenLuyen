"""Short-lived, tamper-proof receipts for browser-to-storage uploads."""

import base64
import binascii
import hashlib
import hmac
import json
import time

from api.app.config import settings
from api.app.schemas.common import AppError


def _encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def issue_upload_ticket(payload: dict) -> str:
    payload = {**payload, "exp": int(time.time()) + 60 * 60 * 2}
    body = _encode(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(settings.SECRET_KEY.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    return f"{body}.{_encode(signature)}"


def verify_upload_ticket(ticket: str) -> dict:
    try:
        body, signature = ticket.split(".", 1)
        expected = hmac.new(settings.SECRET_KEY.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(_decode(signature), expected):
            raise ValueError("Invalid signature")
        payload = json.loads(_decode(body))
        if not isinstance(payload, dict) or int(payload["exp"]) < int(time.time()):
            raise ValueError("Expired ticket")
        return payload
    except (ValueError, KeyError, TypeError, UnicodeDecodeError, binascii.Error) as exc:
        raise AppError(status_code=400, code="INVALID_UPLOAD_TICKET", message="Phiếu tải minh chứng không hợp lệ hoặc đã hết hạn.") from exc
