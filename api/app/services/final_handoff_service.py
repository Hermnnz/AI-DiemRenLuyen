"""Immutable final-score handoff fingerprint and presentation."""

import hashlib
import json

from sqlalchemy.orm import Session

from api.app.models.entities import Campaign, Case, FinalHandoff, ScoreSnapshot, User
from api.app.schemas import format_datetime, format_score


def final_score_fingerprint(db: Session, campaign: Campaign) -> str:
    rows = []
    cases = db.query(Case).filter(Case.campaign_id == campaign.id).order_by(Case.id).all()
    for case in cases:
        student = db.query(User).filter(User.id == case.student_id).one()
        snapshot = db.query(ScoreSnapshot).filter(
            ScoreSnapshot.case_id == case.id, ScoreSnapshot.kind == "FINAL"
        ).first()
        rows.append({
            "case_id": case.id,
            "student_code": student.username,
            "student_name": student.full_name,
            "status": case.status,
            "claimed_total": format_score(case.claimed_total),
            "proposed_total": format_score(case.proposed_total),
            "final_total": format_score(case.final_total),
            "acceptance_source": case.acceptance_source,
            "snapshot": snapshot.per_criterion_json if snapshot else None,
        })
    payload = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def handoff_status(handoff: FinalHandoff | None) -> dict:
    return {
        "status": "NOT_SENT" if handoff is None else ("RECEIVED" if handoff.received_at else "SENT"),
        "snapshot_sha256": handoff.snapshot_sha256 if handoff else None,
        "sent_by": handoff.sent_by if handoff else None,
        "sent_at": format_datetime(handoff.sent_at) if handoff else None,
        "received_by": handoff.received_by if handoff else None,
        "received_at": format_datetime(handoff.received_at) if handoff and handoff.received_at else None,
    }
