"""Identify current evidence requiring an explicit human decision."""

from sqlalchemy.orm import Session

from api.app.models.entities import AiAgentStep, AiReviewRun, BcsEvidenceDecision, Case, Claim, EvidenceFile
from api.app.services.rule_check_service import evaluate_case_rules
from api.app.services.auto_evidence_service import current_auto_accepted


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
