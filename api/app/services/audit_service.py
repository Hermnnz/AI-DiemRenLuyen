from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from api.app.models.entities import AuditEvent


def log_audit(
    db: Session,
    campaign_id: str,
    action: str,
    actor_user_id: Optional[str] = None,
    case_id: Optional[str] = None,
    before_json: Optional[Dict[str, Any]] = None,
    after_json: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_user_id=actor_user_id,
        campaign_id=campaign_id,
        case_id=case_id,
        action=action,
        before_json=before_json,
        after_json=after_json,
        request_id=request_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(event)
    return event
