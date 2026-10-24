"""Private Supabase Storage access. The secret key never reaches the browser."""

from urllib.parse import quote

import httpx

from api.app.config import settings
from api.app.schemas.common import AppError


def remote_storage_enabled() -> bool:
    return settings.STORAGE_BACKEND == "supabase"


def _base_url() -> str:
    if not settings.SUPABASE_URL or not settings.SUPABASE_SECRET_KEY:
        raise AppError(
            status_code=503,
            code="STORAGE_NOT_CONFIGURED",
            message="Kho minh chứng trực tuyến chưa được cấu hình.",
        )
    return settings.SUPABASE_URL.rstrip("/") + "/storage/v1"


def _object_path(storage_key: str) -> str:
    bucket = quote(settings.SUPABASE_BUCKET, safe="")
    key = quote(storage_key, safe="/")
    return f"{bucket}/{key}"


def _headers() -> dict[str, str]:
    headers = {"apikey": settings.SUPABASE_SECRET_KEY}
    # New sb_secret_* keys are API keys, not JWTs. Legacy service_role JWTs
    # still need the bearer header for Storage authorization.
    if not settings.SUPABASE_SECRET_KEY.startswith("sb_secret_"):
        headers["Authorization"] = f"Bearer {settings.SUPABASE_SECRET_KEY}"
    return headers


def _signed_url(url: str) -> str:
    if url.startswith("https://"):
        return url
    return _base_url() + "/" + url.lstrip("/")


def create_upload_url(storage_key: str) -> str:
    url = f"{_base_url()}/object/upload/sign/{_object_path(storage_key)}"
    try:
        with httpx.Client(timeout=20) as client:
            response = client.post(url, headers=_headers())
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise AppError(status_code=502, code="STORAGE_ERROR", message="Không tạo được liên kết tải minh chứng lên.") from exc
    signed = data.get("url") or data.get("signedURL")
    if not isinstance(signed, str):
        raise AppError(status_code=502, code="STORAGE_ERROR", message="Kho minh chứng trả về liên kết không hợp lệ.")
    return _signed_url(signed)


def download_object(storage_key: str) -> bytes:
    url = f"{_base_url()}/object/authenticated/{_object_path(storage_key)}"
    try:
        with httpx.Client(timeout=45) as client:
            response = client.get(url, headers=_headers())
            if response.status_code == 404:
                raise AppError(status_code=404, code="FILE_NOT_FOUND", message="Tệp minh chứng chưa được tải lên.")
            response.raise_for_status()
            return response.content
    except httpx.HTTPError as exc:
        raise AppError(status_code=502, code="STORAGE_ERROR", message="Không đọc được tệp minh chứng trực tuyến.") from exc


def create_download_url(storage_key: str) -> str:
    url = f"{_base_url()}/object/sign/{_object_path(storage_key)}"
    try:
        with httpx.Client(timeout=20) as client:
            response = client.post(url, headers=_headers(), json={"expiresIn": 60})
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise AppError(status_code=502, code="STORAGE_ERROR", message="Không tạo được liên kết xem minh chứng.") from exc
    signed = data.get("signedURL") or data.get("signedUrl")
    if not isinstance(signed, str):
        raise AppError(status_code=502, code="STORAGE_ERROR", message="Kho minh chứng trả về liên kết không hợp lệ.")
    return _signed_url(signed)
