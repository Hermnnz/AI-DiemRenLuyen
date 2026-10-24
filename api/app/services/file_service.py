import os
import uuid
import hashlib
from typing import Tuple
from fastapi import UploadFile
from api.app.config import settings
from api.app.schemas.common import AppError

ALLOWED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


def ensure_storage_dir():
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)


async def save_upload_file(file: UploadFile) -> Tuple[str, str, int, str]:
    """
    Xác thực MIME type, kích thước và lưu tệp an toàn vào STORAGE_DIR.
    Trả về: (storage_key, original_name, size_bytes, sha256_hash)
    """
    content_type = file.content_type or ""
    if content_type not in ALLOWED_MIME_TYPES:
        raise AppError(
            status_code=422,
            code="INVALID_FILE_TYPE",
            message=f"Định dạng tệp '{content_type}' không được hỗ trợ. Chỉ chấp nhận PDF, JPG, PNG.",
            fields={"file": "Chỉ chấp nhận application/pdf, image/jpeg, image/png"}
        )

    ensure_storage_dir()

    content = await file.read()
    size_bytes = len(content)
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    if size_bytes > max_bytes:
        raise AppError(
            status_code=422,
            code="FILE_TOO_LARGE",
            message=f"Kích thước tệp ({size_bytes / (1024 * 1024):.2f} MB) vượt quá giới hạn cho phép ({settings.MAX_UPLOAD_SIZE_MB} MB).",
            fields={"file": f"Kích thước tối đa là {settings.MAX_UPLOAD_SIZE_MB} MB"}
        )

    sha256 = hashlib.sha256(content).hexdigest()
    storage_key = f"{uuid.uuid4()}{ALLOWED_MIME_TYPES[content_type]}"
    file_path = os.path.join(settings.STORAGE_DIR, storage_key)

    with open(file_path, "wb") as f:
        f.write(content)

    return storage_key, file.filename or "unknown", size_bytes, sha256


def get_file_path(storage_key: str) -> str:
    path = os.path.join(settings.STORAGE_DIR, storage_key)
    if not os.path.exists(path):
        raise AppError(
            status_code=404,
            code="FILE_NOT_FOUND",
            message="Không tìm thấy tệp trên hệ thống lưu trữ.",
        )
    return path
