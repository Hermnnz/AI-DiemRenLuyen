"""Versioned draft-score review checkpoint between the two meetings."""

import hashlib
import json

from sqlalchemy.orm import Session

from api.app.models.entities import AuditEvent, Campaign, Case, Claim, Criterion, Meeting
from api.app.schemas import format_datetime, format_score


def draft_fingerprint(db: Session, campaign: Campaign) -> str:
    bcs_meeting = db.query(Meeting).filter(Meeting.campaign_id == campaign.id, Meeting.kind == "BCS").first()
    cases = db.query(Case).filter(Case.campaign_id == campaign.id).order_by(Case.id).all()
    rows = []
    for case in cases:
        claims = db.query(Claim).filter(Claim.case_id == case.id).order_by(Claim.criterion_id).all()
        rows.append({
            "case_id": case.id, "status": case.status, "version": case.version,
            "proposed_total": format_score(case.proposed_total),
            "claims": [{"criterion_id": claim.criterion_id, "approved_score": format_score(claim.approved_score),
                        "bcs_reason": claim.bcs_reason} for claim in claims],
        })
    payload = {
        "meeting": {"held_at": format_datetime(bcs_meeting.held_at), "note": bcs_meeting.note} if bcs_meeting else None,
        "criteria": [{"id": item.id, "code": item.code, "title": item.title,
                      "description": item.description, "max_score": format_score(item.max_score),
                      "requires_evidence": item.requires_evidence, "rule_config": item.rule_config}
                     for item in db.query(Criterion).filter(Criterion.campaign_id == campaign.id).order_by(Criterion.id).all()],
        "cases": rows,
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def draft_review_status(db: Session, campaign: Campaign) -> dict:
    current = draft_fingerprint(db, campaign)
    latest = (
        db.query(AuditEvent)
        .filter(AuditEvent.campaign_id == campaign.id, AuditEvent.action == "DRAFT_REVIEW_CONFIRMED")
        .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .first()
    )
    reviewed = bool(latest and latest.after_json and latest.after_json.get("fingerprint") == current)
    return {
        "fingerprint": current,
        "reviewed": reviewed,
        "reviewed_at": format_datetime(latest.created_at) if reviewed else None,
    }
