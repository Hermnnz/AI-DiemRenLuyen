"""Identify current evidence requiring an explicit human decision."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from api.app.models.entities import AiAgentStep, AiReviewRun, BcsEvidenceDecision, Case, Claim, EvidenceFile
from api.app.services.rule_check_service import evaluate_case_rules
from api.app.services.auto_evidence_service import current_auto_accepted
from api.app.services.audit_service import log_audit
from api.app.services.scoring_service import sum_scores


def zero_score_if_all_evidence_rejected(
    db: Session, case: Case, claim: Claim, reviewer_id: str, now: datetime,
) -> dict | None:
    """A final BCS rejection of every current file also decides the score as zero.

    Other criteria and the student's original self-score remain unchanged.
    Callers flush the evidence decision first and commit both changes together.
    """
    rows = (db.query(EvidenceFile.id, BcsEvidenceDecision.decision, BcsEvidenceDecision.reason)
            .outerjoin(BcsEvidenceDecision, BcsEvidenceDecision.evidence_file_id == EvidenceFile.id)
            .filter(EvidenceFile.claim_id == claim.id, EvidenceFile.is_current.is_(True))
            .order_by(EvidenceFile.id).all())
    if not rows or any(row.decision != "REJECT_ITEM" for row in rows):
        return None
    reasons = list(dict.fromkeys(row.reason.strip() for row in rows if row.reason and row.reason.strip()))
    reason = "BCS đã từ chối toàn bộ minh chứng hiện tại của tiêu chí; tự động lưu điểm duyệt 0."
    if reasons:
        reason += " Căn cứ: " + " | ".join(reasons)
    if claim.approved_score != Decimal("0.00") or claim.bcs_reason != reason:
        before = {"approved_score": str(claim.approved_score) if claim.approved_score is not None else None,
                  "bcs_reason": claim.bcs_reason}
        claim.approved_score = Decimal("0.00")
        claim.bcs_reason = reason
        claim.reviewed_by = reviewer_id
        claim.reviewed_at = now
        if case.proposed_total is not None:
            case.proposed_total = sum_scores([
                item.approved_score for item in db.query(Claim).filter(Claim.case_id == case.id).all()
            ])
        log_audit(
            db, campaign_id=case.campaign_id, case_id=case.id, actor_user_id=reviewer_id,
            action="BCS_SCORE_ZEROED_AFTER_EVIDENCE_REJECTION", before_json=before,
            after_json={"criterion_id": claim.criterion_id, "approved_score": "0.00",
                        "bcs_reason": reason, "evidence_file_ids": [row.id for row in rows]},
        )
    return {"criterion_id": claim.criterion_id, "approved_score": "0.00", "bcs_reason": claim.bcs_reason}


def required_evidence_file_ids(db: Session, case: Case) -> set[str]:
    current_files = (
        db.query(EvidenceFile)
        .join(Claim, EvidenceFile.claim_id == Claim.id)
        .filter(Claim.case_id == case.id, EvidenceFile.is_current.is_(True))
        .all()
    )
    by_id = {file.id: file for file in current_files}
    by_criterion: dict[str, set[str]] = {}
    for file in current_files:
        by_criterion.setdefault(file.claim.criterion_id, set()).add(file.id)

    # Every positively claimed file needs either an AI acceptance or a BCS
    # decision. No AI result, UNKNOWN and FLAGGED all stay in the human lane.
    required: set[str] = {file.id for file in current_files
                          if file.claim.self_score is not None and file.claim.self_score > 0}
    for finding in evaluate_case_rules(db, case)["findings"]:
        if finding["level"] not in {"FLAGGED", "UNKNOWN"}:
            continue
        file_ids = finding["evidence_file_ids"]
        if file_ids:
            required.update(file_id for file_id in file_ids if file_id in by_id)
        elif finding["criterion_id"]:
            required.update(by_criterion.get(finding["criterion_id"], set()))

    steps = (
        db.query(AiAgentStep)
        .join(AiReviewRun, AiAgentStep.run_id == AiReviewRun.id)
        .filter(AiReviewRun.case_id == case.id, AiAgentStep.kind.in_(["AI_READ", "AI_TRANSPARENCY"]))
        .all()
    )
    for step in steps:
        if not isinstance(step.output_json, dict):
            continue
        items = step.output_json.get("files" if step.kind == "AI_READ" else "assessments", [])
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            file = by_id.get(item.get("evidence_file_id"))
            if file and item.get("sha256") == file.sha256:
                required.add(file.id)

    # AI acceptance replaces the per-file BCS decision only while its exact
    # rubric, self-score, term and evidence snapshot still match.
    required.difference_update(item["evidence_file_id"] for item in current_auto_accepted(db, case))

    # A pending human decision remains actionable after a proof timeout.
    pending = (
        db.query(BcsEvidenceDecision.evidence_file_id)
        .filter(BcsEvidenceDecision.evidence_file_id.in_(by_id),
                BcsEvidenceDecision.decision.in_(["HOLD", "REQUEST_SUPPLEMENT"]))
        .all()
        if by_id else []
    )
    required.update(file_id for (file_id,) in pending)
    return required
