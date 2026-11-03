from typing import Optional
from datetime import datetime, timezone, timedelta
import uuid
from sqlalchemy.orm import Session
from api.app.models.entities import BcsEvidenceDecision, ClassMember, Notification, User


VIETNAM_TIMEZONE = timezone(timedelta(hours=7))
BCS_EVIDENCE_REVIEW = "BCS_EVIDENCE_REVIEW"


def format_notification_deadline(value: datetime) -> str:
    """DB timestamps without an offset are UTC, just like API timestamps."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    local = value.astimezone(VIETNAM_TIMEZONE)
    return local.strftime("%d/%m/%Y %H:%M") + " (giờ Việt Nam, UTC+7)"


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


def notify_bcs_evidence_review(db: Session, case, run_id: str) -> None:
    """Group current evidence still needing a decision into one alert per run."""
    if case.status != "BCS_REVIEW":
        return
    from api.app.services.evidence_decision_service import required_evidence_file_ids

    db.flush()
    pending = required_evidence_file_ids(db, case)
    if not pending:
        return
    decided = db.query(BcsEvidenceDecision.evidence_file_id).filter(
        BcsEvidenceDecision.evidence_file_id.in_(pending),
        BcsEvidenceDecision.decision.in_(("ACCEPT", "REJECT_ITEM")),
    )
    count = len(pending.difference(file_id for (file_id,) in decided))
    if not count:
        return
    recipients = db.query(User.id).join(ClassMember, ClassMember.user_id == User.id).filter(
        ClassMember.class_id == case.campaign.class_id,
        ClassMember.member_role == "BCS",
        User.role == "BCS",
        User.is_active.is_(True),
    )
    for (user_id,) in recipients:
        send_notification(
            db, user_id=user_id, type=BCS_EVIDENCE_REVIEW,
            title=f"Hồ sơ {case.student.username} có minh chứng cần xem xét",
            body=f"Còn {count} minh chứng cần BCS kết luận. Mở hồ sơ để xem lý do từng tệp.",
            case_id=case.id, dedup_key=f"bcs_evidence_{run_id}_{user_id}",
        )
