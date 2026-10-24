from typing import Optional
from datetime import datetime, timezone
import uuid
from sqlalchemy.orm import Session
from api.app.models.entities import Notification


def send_notification(
    db: Session,
    user_id: str,
    type: str,
    title: str,
    body: str,
    case_id: Optional[str] = None,
    dedup_key: Optional[str] = None,
) -> Optional[Notification]:
    if dedup_key is None:
        dedup_key = f"{user_id}_{type}_{uuid.uuid4()}"

    existing = db.query(Notification).filter(Notification.dedup_key == dedup_key).first()
    if existing:
        return None

    notification = Notification(
        user_id=user_id,
        case_id=case_id,
        type=type,
        title=title,
        body=body,
        dedup_key=dedup_key,
        created_at=datetime.now(timezone.utc),
    )
    db.add(notification)
    return notification
