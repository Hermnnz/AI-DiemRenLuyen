"""Service for recording BCS feedback on AI evidence assessments, detecting discrepancies,
and managing ground-truth verification for AI pilot quality evaluation.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from api.app.models.entities import (
    AiReviewRun,
    AuditEvent,
    BcsAiFeedback,
    Case,
    Criterion,
    EvidenceFile,
    User,
)
from api.app.schemas.common import AppError
from api.app.services.ai_review_service import PIPELINE_VERSION, build_case_snapshot
from api.app.services.audit_service import log_audit


def record_bcs_ai_feedback(
    db: Session,
    evidence: EvidenceFile,
    case: Case,
    bcs_decision: str,
    bcs_reason: str,
    user_id: str,
    now: datetime,
) -> BcsAiFeedback:
    """Automatically links a BCS evidence decision to the matching AI assessment of that EXACT file.

    Uses evidence_file_id, version_no, and sha256 to ensure exact match.
    If no matching completed/fresh AI run exists, records 'no AI result' status.
    """
    # 1. Resolve criterion code
    criterion_id = evidence.claim.criterion_id
    criterion = db.query(Criterion).filter(Criterion.id == criterion_id).first()
    criterion_code = criterion.code if criterion else "UNKNOWN"

    # 2. Search for matching completed AI review run for this case
    runs = (
        db.query(AiReviewRun)
        .filter(AiReviewRun.case_id == case.id)
        .order_by(AiReviewRun.created_at.desc(), AiReviewRun.id.desc())
        .all()
    )

    matching_status: str = "NO_AI_RUN"
    ai_run: Optional[AiReviewRun] = None
    ai_assessment: Optional[Dict[str, Any]] = None

    if runs:
        latest_run = runs[0]
        # Check staleness of the AI run for this evidence decision
        rubric_version, evidence_fingerprint, _ = build_case_snapshot(db, case)
        snapshot_evidence = (latest_run.snapshot_json or {}).get("evidence", [])
        file_in_snapshot = next(
            (item for item in snapshot_evidence if item.get("id") == evidence.id),
            None,
        )

        is_run_stale = (
            latest_run.status == "STALE"
            or (latest_run.rubric_version is not None and latest_run.rubric_version != rubric_version)
            or (latest_run.evidence_fingerprint is not None and latest_run.evidence_fingerprint != evidence_fingerprint)
            or not file_in_snapshot
            or file_in_snapshot.get("sha256") != evidence.sha256
            or file_in_snapshot.get("version_no") != evidence.version_no
        )

        if is_run_stale:
            matching_status = "STALE_AI_RUN"
            ai_run = latest_run
        elif latest_run.status not in ["COMPLETED", "NEEDS_HUMAN"]:
            matching_status = "NO_AI_RUN"
            ai_run = latest_run
        else:
            # Inspect AI_TRANSPARENCY step for assessment of this file
            transparency_step = next(
                (s for s in latest_run.steps if s.kind == "AI_TRANSPARENCY" and s.status == "COMPLETED"),
                None,
            )
            assessments = (transparency_step.output_json or {}).get("assessments", []) if transparency_step else []
            file_assessment = next(
                (a for a in assessments if a.get("evidence_file_id") == evidence.id and a.get("sha256") == evidence.sha256),
                None,
            )

            if file_assessment and transparency_step:
                matching_status = "MATCHED"
                ai_run = latest_run
                ai_assessment = file_assessment
            else:
                # Do NOT infer transparency verdict from AI_READ!
                # If no assessment in AI_TRANSPARENCY, mark as missing AI result and exclude from metrics
                matching_status = "NO_MATCHING_ASSESSMENT"
                ai_run = latest_run
                ai_assessment = None

    # 3. Determine discrepancy status (Requirement 3)
    if matching_status != "MATCHED" or not ai_assessment:
        discrepancy_status = "NO_AI_RESULT"
    else:
        ai_verdict = ai_assessment.get("verdict")
        dual_gate_run = (ai_run.result_json or {}).get("pipeline_version") == PIPELINE_VERSION
        auto_accepted = any(
            item.get("evidence_file_id") == evidence.id and item.get("sha256") == evidence.sha256
            for item in (ai_run.result_json or {}).get("auto_accepted_evidence", [])
        ) if dual_gate_run else False
        # REQUEST_SUPPLEMENT and HOLD are non-final; never treat as AI right or wrong
        if bcs_decision in ["REQUEST_SUPPLEMENT", "HOLD"]:
            discrepancy_status = "NON_FINAL_DECISION"
        elif dual_gate_run and ai_verdict == "SUPPORTED" and not auto_accepted:
            # The first prompt supported it, but the two-gate AI made no acceptance decision.
            discrepancy_status = "NON_FINAL_DECISION"
        elif bcs_decision == "ACCEPT":
            if ai_verdict == "SUPPORTED":
                discrepancy_status = "AGREED"
            else:
                # AI flagged or unknown, but BCS accepted -> potential discrepancy to review
                discrepancy_status = "NEEDS_REVIEW"
        elif bcs_decision == "REJECT_ITEM":
            if ai_verdict == "FLAGGED":
                discrepancy_status = "AGREED"
            else:
                # AI supported or unknown, but BCS rejected -> potential discrepancy to review
                discrepancy_status = "NEEDS_REVIEW"
        else:
            discrepancy_status = "NON_FINAL_DECISION"

    # Distinguish between Gemini-created assessment and system fallback (model=None)
    if ai_assessment:
        if "model" in ai_assessment:
            ai_model = ai_assessment.get("model")
        else:
            ai_model = ai_run.model if ai_run else None
        ai_prompt_version = ai_assessment.get("prompt_version") or (ai_run.prompt_version if ai_run else None)
        ai_verdict = ai_assessment.get("verdict")
        ai_reason = ai_assessment.get("reason")
    else:
        ai_model = None
        ai_prompt_version = None
        ai_verdict = None
        ai_reason = None

    # 4. Upsert feedback record and preserve audit trail (Requirement 2)
    existing = db.query(BcsAiFeedback).filter(BcsAiFeedback.evidence_file_id == evidence.id).first()

    if existing:
        old_bcs_decision = existing.bcs_decision
        decision_changed = (old_bcs_decision != bcs_decision)

        before_json = {
            "evidence_file_id": existing.evidence_file_id,
            "bcs_decision": existing.bcs_decision,
            "bcs_reason": existing.bcs_reason,
            "reviewed_by": existing.reviewed_by,
            "reviewed_at": existing.reviewed_at.isoformat() if existing.reviewed_at else None,
            "ai_run_id": existing.ai_run_id,
            "ai_verdict": existing.ai_verdict,
            "matching_status": existing.matching_status,
            "discrepancy_status": existing.discrepancy_status,
            "ground_truth_status": existing.ground_truth_status,
            "ground_truth_label": existing.ground_truth_label,
            "verification_reason": existing.verification_reason,
            "verified_by": existing.verified_by,
            "verified_at": existing.verified_at.isoformat() if existing.verified_at else None,
        }

        existing.file_sha256 = evidence.sha256
        existing.file_version_no = evidence.version_no
        existing.bcs_decision = bcs_decision
        existing.bcs_reason = bcs_reason
        existing.reviewed_by = user_id
        existing.reviewed_at = now
        existing.ai_run_id = ai_run.id if ai_run else None
        existing.ai_model = ai_model
        existing.ai_prompt_version = ai_prompt_version
        existing.ai_verdict = ai_verdict
        existing.ai_reason = ai_reason
        existing.ai_assessment_json = ai_assessment
        existing.matching_status = matching_status
        existing.discrepancy_status = discrepancy_status
        existing.updated_at = now

        # Reset ground truth if decision changed, requiring fresh review
        if decision_changed:
            existing.ground_truth_status = "UNVERIFIED"
            existing.ground_truth_label = None
            existing.verification_reason = None
            existing.verified_by = None
            existing.verified_at = None

        log_audit(
            db,
            campaign_id=case.campaign_id,
            case_id=case.id,
            action="BCS_AI_FEEDBACK_UPDATED",
            actor_user_id=user_id,
            before_json=before_json,
            after_json={
                "evidence_file_id": evidence.id,
                "file_sha256": evidence.sha256,
                "file_version_no": evidence.version_no,
                "old_bcs_decision": old_bcs_decision,
                "bcs_decision": bcs_decision,
                "bcs_reason": bcs_reason,
                "ai_run_id": existing.ai_run_id,
                "ai_verdict": ai_verdict,
                "matching_status": matching_status,
                "discrepancy_status": discrepancy_status,
                "ground_truth_status": existing.ground_truth_status,
                "ground_truth_label": existing.ground_truth_label,
            },
        )
        return existing

    record = BcsAiFeedback(
        evidence_file_id=evidence.id,
        file_sha256=evidence.sha256,
        file_version_no=evidence.version_no,
        case_id=case.id,
        criterion_id=criterion_id,
        criterion_code=criterion_code,
        bcs_decision=bcs_decision,
        bcs_reason=bcs_reason,
        reviewed_by=user_id,
        reviewed_at=now,
        ai_run_id=ai_run.id if ai_run else None,
        ai_model=ai_model,
        ai_prompt_version=ai_prompt_version,
        ai_verdict=ai_verdict,
        ai_reason=ai_reason,
        ai_assessment_json=ai_assessment,
        matching_status=matching_status,
        discrepancy_status=discrepancy_status,
        ground_truth_status="UNVERIFIED",
        ground_truth_label=None,
        created_at=now,
        updated_at=now,
    )
    db.add(record)
    log_audit(
        db,
        campaign_id=case.campaign_id,
        case_id=case.id,
        action="BCS_AI_FEEDBACK_RECORDED",
        actor_user_id=user_id,
        before_json=None,
        after_json={
            "evidence_file_id": evidence.id,
            "file_sha256": evidence.sha256,
            "file_version_no": evidence.version_no,
            "bcs_decision": bcs_decision,
            "bcs_reason": bcs_reason,
            "ai_run_id": record.ai_run_id,
            "ai_verdict": ai_verdict,
            "matching_status": matching_status,
            "discrepancy_status": discrepancy_status,
        },
    )
    return record


def verify_ground_truth(
    db: Session,
    feedback_id: str,
    ground_truth_label: str,
    reason: str,
    user_id: str,
) -> BcsAiFeedback:
    """Verifies a ground truth label for an evaluation feedback record (Requirement 4)."""
    feedback = db.query(BcsAiFeedback).filter(BcsAiFeedback.id == feedback_id).first()
    if not feedback:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy bản ghi phản hồi.")

    clean_label = ground_truth_label.strip().upper()
    if clean_label not in {"SUPPORTED", "FLAGGED", "UNKNOWN"}:
        raise AppError(
            status_code=422,
            code="INVALID_LABEL",
            message="Nhãn chuẩn phải là SUPPORTED, FLAGGED hoặc UNKNOWN.",
        )

    clean_reason = reason.strip()
    if not clean_reason:
        raise AppError(
            status_code=422,
            code="REASON_REQUIRED",
            message="Hãy ghi rõ căn cứ xác nhận nhãn chuẩn cho ca đánh giá này.",
        )

    now = datetime.now(timezone.utc)
    before_json = {
        "ground_truth_status": feedback.ground_truth_status,
        "ground_truth_label": feedback.ground_truth_label,
        "verification_reason": feedback.verification_reason,
        "verified_by": feedback.verified_by,
        "verified_at": feedback.verified_at.isoformat() if feedback.verified_at else None,
    }

    feedback.ground_truth_status = "VERIFIED"
    feedback.ground_truth_label = clean_label
    feedback.verification_reason = clean_reason
    feedback.verified_by = user_id
    feedback.verified_at = now
    feedback.updated_at = now

    case = feedback.case
    campaign_id = case.campaign_id if case else None

    log_audit(
        db,
        campaign_id=campaign_id,
        case_id=feedback.case_id,
        action="AI_GROUND_TRUTH_VERIFIED",
        actor_user_id=user_id,
        before_json=before_json,
        after_json={
            "feedback_id": feedback.id,
            "evidence_file_id": feedback.evidence_file_id,
            "ground_truth_label": clean_label,
            "verification_reason": clean_reason,
            "verified_by": user_id,
            "verified_at": now.isoformat(),
        },
    )
    db.commit()
    db.refresh(feedback)
    return feedback


def calculate_ai_feedback_metrics(
    db: Session,
    campaign_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculates AI quality metrics.

    CRITICAL RULE (Requirement 4 & 6):
    Only records with ground_truth_status == 'VERIFIED' and matching_status == 'MATCHED'
    are included in accuracy / precision / confusion matrix metrics!
    """
    query = db.query(BcsAiFeedback)
    if campaign_id:
        query = query.join(Case, BcsAiFeedback.case_id == Case.id).filter(Case.campaign_id == campaign_id)

    records = query.all()

    total_count = len(records)
    matched_count = sum(1 for r in records if r.matching_status == "MATCHED")
    no_ai_count = sum(1 for r in records if r.matching_status == "NO_AI_RUN")
    stale_ai_count = sum(1 for r in records if r.matching_status == "STALE_AI_RUN")
    agreed_count = sum(1 for r in records if r.discrepancy_status == "AGREED")
    discrepancy_count = sum(1 for r in records if r.discrepancy_status == "NEEDS_REVIEW")
    non_final_count = sum(1 for r in records if r.discrepancy_status == "NON_FINAL_DECISION")
    unverified_count = sum(1 for r in records if r.ground_truth_status == "UNVERIFIED")
    verified_count = sum(1 for r in records if r.ground_truth_status == "VERIFIED")

    # Strict ground-truth evaluation subset
    # Rule: Only genuine model assessments (ai_model is not None) are evaluated in AI quality metrics!
    # System fallback assessments (model=None) are excluded from AI accuracy and confusion matrix.
    verified_matched = [
        r for r in records
        if r.ground_truth_status == "VERIFIED"
        and r.matching_status == "MATCHED"
        and r.ground_truth_label
        and r.ai_model is not None
    ]

    verified_matched_count = len(verified_matched)

    if verified_matched_count == 0:
        return {
            "total_count": total_count,
            "matched_count": matched_count,
            "no_ai_count": no_ai_count,
            "stale_ai_count": stale_ai_count,
            "agreed_count": agreed_count,
            "discrepancy_count": discrepancy_count,
            "non_final_count": non_final_count,
            "unverified_count": unverified_count,
            "verified_count": verified_count,
            "verified_matched_count": 0,
            "ai_accuracy": None,
            "ai_precision_supported": None,
            "ai_recall_supported": None,
            "confusion_matrix": None,
            "message": "Chưa có ca nào được xác nhận nhãn chuẩn. Chỉ số AI chỉ được tính trên các ca đã xác nhận.",
        }

    # Confusion matrix: AI Verdict (Row) vs Ground Truth (Column)
    labels = ["SUPPORTED", "FLAGGED", "UNKNOWN"]
    matrix = {row: {col: 0 for col in labels} for row in labels}
    correct_count = 0

    for r in verified_matched:
        pred = r.ai_verdict if r.ai_verdict in labels else "UNKNOWN"
        gt = r.ground_truth_label if r.ground_truth_label in labels else "UNKNOWN"
        matrix[pred][gt] += 1
        if pred == gt:
            correct_count += 1

    accuracy = round(correct_count / verified_matched_count, 4)

    # Precision & recall for SUPPORTED
    pred_supported = sum(matrix["SUPPORTED"].values())
    gt_supported = sum(matrix[row]["SUPPORTED"] for row in labels)
    tp_supported = matrix["SUPPORTED"]["SUPPORTED"]

    precision_supported = round(tp_supported / pred_supported, 4) if pred_supported > 0 else None
    recall_supported = round(tp_supported / gt_supported, 4) if gt_supported > 0 else None

    # Discrepancy resolution summary on verified cases
    discrepancy_verified = [r for r in verified_matched if r.discrepancy_status == "NEEDS_REVIEW"]
    ai_aligned_with_gt_in_discrepancy = sum(1 for r in discrepancy_verified if r.ai_verdict == r.ground_truth_label)

    return {
        "total_count": total_count,
        "matched_count": matched_count,
        "no_ai_count": no_ai_count,
        "stale_ai_count": stale_ai_count,
        "agreed_count": agreed_count,
        "discrepancy_count": discrepancy_count,
        "non_final_count": non_final_count,
        "unverified_count": unverified_count,
        "verified_count": verified_count,
        "verified_matched_count": verified_matched_count,
        "ai_accuracy": accuracy,
        "ai_precision_supported": precision_supported,
        "ai_recall_supported": recall_supported,
        "confusion_matrix": matrix,
        "discrepancy_resolution": {
            "verified_discrepancy_count": len(discrepancy_verified),
            "ai_correct_in_discrepancy": ai_aligned_with_gt_in_discrepancy,
            "bcs_correct_in_discrepancy": len(discrepancy_verified) - ai_aligned_with_gt_in_discrepancy,
        },
        "message": f"Chỉ số được tính toán trên {verified_matched_count} ca đã được xác nhận nhãn chuẩn độc lập.",
    }


def get_feedback_audit_history(db: Session, evidence_file_id: str) -> List[Dict[str, Any]]:
    """Retrieves chronological audit history for decisions and verifications on an evidence file."""
    events = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.action.in_([
                "BCS_AI_FEEDBACK_RECORDED",
                "BCS_AI_FEEDBACK_UPDATED",
                "AI_GROUND_TRUTH_VERIFIED",
                "BCS_EVIDENCE_DECIDED",
            ])
        )
        .order_by(AuditEvent.created_at.asc())
        .all()
    )

    history = []
    for ev in events:
        after = ev.after_json or {}
        before = ev.before_json or {}
        if after.get("evidence_file_id") == evidence_file_id or before.get("evidence_file_id") == evidence_file_id:
            actor = db.query(User).filter(User.id == ev.actor_user_id).first()
            history.append({
                "action": ev.action,
                "actor_name": actor.full_name if actor else "Hệ thống",
                "actor_role": actor.role if actor else None,
                "created_at": ev.created_at.isoformat() if ev.created_at else None,
                "before": before,
                "after": after,
            })
    return history
