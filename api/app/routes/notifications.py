from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from api.app.database import get_db
from api.app.models.entities import Notification, User
from api.app.schemas import (
    NotificationItem,
    ReadNotificationResponse,
    AppError,
    format_datetime,
)
from api.app.services.auth_service import get_current_user, verify_csrf

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=List[NotificationItem])
def get_user_notifications(
    auth_data: tuple[User, list[str]] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user, _ = auth_data
    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )

    return [
        NotificationItem(
            id=n.id,
            case_id=n.case_id,
            title=n.title,
            body=n.body,
            type=n.type,
            read_at=format_datetime(n.read_at),
            created_at=format_datetime(n.created_at),
        )
        for n in notifications
    ]


@router.post("/{id}/read", response_model=ReadNotificationResponse, dependencies=[Depends(verify_csrf)])
def mark_notification_read(
    id: str,
    auth_data: tuple[User, list[str]] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user, _ = auth_data
    notif = db.query(Notification).filter(Notification.id == id).first()
    if not notif:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy thông báo.")

    if notif.user_id != user.id:
        raise AppError(status_code=403, code="FORBIDDEN", message="Bạn không có quyền chỉnh sửa thông báo này.")

    now = datetime.now(timezone.utc)
    if not notif.read_at:
        notif.read_at = now
        db.commit()
        db.refresh(notif)

    return ReadNotificationResponse(
        id=notif.id,
        read_at=format_datetime(notif.read_at),
    )
