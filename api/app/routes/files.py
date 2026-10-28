from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session
from api.app.database import get_db
from api.app.models.entities import EvidenceFile, Claim, Case, Campaign, User
from api.app.schemas import AppError
from api.app.services.auth_service import get_current_user
from api.app.services.file_service import get_file_path
from api.app.services.remote_storage import create_download_url, remote_storage_enabled

router = APIRouter(prefix="/files", tags=["Files"])


@router.get("/{fileId}")
def get_file(
    fileId: str,
    auth_data: tuple[User, list[str]] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user, class_ids = auth_data

    ev = db.query(EvidenceFile).filter(EvidenceFile.id == fileId, EvidenceFile.is_current.is_(True)).first()
    if not ev:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy tệp minh chứng.")

    claim = db.query(Claim).filter(Claim.id == ev.claim_id).first()
    if not claim:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy yêu cầu minh chứng liên quan.")

    case = db.query(Case).filter(Case.id == claim.case_id).first()
    campaign = db.query(Campaign).filter(Campaign.id == case.campaign_id).first()

    # RBAC check: Only owner student or class BCS can access evidence files
    if user.role == "STUDENT":
        if case.student_id != user.id:
            raise AppError(
                status_code=403,
                code="FORBIDDEN",
                message="Bạn không có quyền truy cập minh chứng của sinh viên khác."
            )
    elif user.role == "BCS":
        if campaign.class_id not in class_ids:
            raise AppError(
                status_code=403,
                code="FORBIDDEN",
                message="Bạn không có quyền truy cập minh chứng của lớp khác."
            )
    elif user.role == "ADMIN":
        pass
    else:
        raise AppError(
            status_code=403,
            code="FORBIDDEN",
            message="Vai trò của bạn không được phép xem minh chứng trực tiếp."
        )

    if remote_storage_enabled():
        return RedirectResponse(url=create_download_url(ev.storage_key), status_code=307)

    file_path = get_file_path(ev.storage_key)

    return FileResponse(
        path=file_path,
        media_type=ev.mime_type,
        filename=ev.original_name,
    )
