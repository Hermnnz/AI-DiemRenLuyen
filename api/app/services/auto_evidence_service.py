"""Provisional AI acceptance of visible evidence; BCS retains the final score decision."""

import re
import unicodedata

from sqlalchemy.orm import Session

from api.app.config import settings
from api.app.models.entities import AiReviewRun, Case, Claim, EvidenceFile


REQUIRED_FACT_KINDS = {"recipient", "activity_name", "event_date", "issuer"}


def _person_key(value: str) -> str:
    value = unicodedata.normalize("NFD", value.casefold().replace("đ", "d"))
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def select_auto_accepted(
    db: Session, case: Case, run: AiReviewRun, reads: list[dict],
    assessments: list[dict], rule_checks: dict, *, require_self_review: bool = True,
) -> list[dict]:
    """Accept only exact current files with cited identity, activity, issuer and date."""
    if not (settings.AI_AUTO_ACCEPT_ENABLED and settings.AI_READ_ENABLED
            and settings.AI_TRANSPARENCY_ENABLED and settings.GEMINI_API_KEY):
        return []
    threshold = settings.AI_AUTO_ACCEPT_THRESHOLD
    if not 0 <= threshold <= 1 or rule_checks.get("term_window", {}).get("status") != "CONFIGURED":
        return []
    if rule_checks.get("date_evidence_status") != "CHECKED":
        return []

    snapshot_files = {item["id"]: item for item in run.snapshot_json.get("evidence", [])}
    reads_by_file = {(item.get("evidence_file_id"), item.get("sha256")): item for item in reads}
    current_files = (
        db.query(EvidenceFile).join(Claim, EvidenceFile.claim_id == Claim.id)
        .filter(Claim.case_id == case.id, EvidenceFile.is_current.is_(True)).all()
    )
    by_id = {file.id: file for file in current_files}
    accepted: list[dict] = []
    for assessment in assessments:
        file_id, sha = assessment.get("evidence_file_id"), assessment.get("sha256")
        file = by_id.get(file_id)
        snapshot = snapshot_files.get(file_id)
        read = reads_by_file.get((file_id, sha))
        confidence = assessment.get("confidence")
        self_review = assessment.get("self_review") or {}
        self_confidence = self_review.get("confidence")
        if (not file or not snapshot or not read or not read.get("readable")
                or file.sha256 != sha or snapshot.get("sha256") != sha
                or snapshot.get("version_no") != file.version_no
                or assessment.get("verdict") != "SUPPORTED"
                or assessment.get("raw_verdict", "SUPPORTED") != "SUPPORTED"
                or assessment.get("post_processing_reason")
                or assessment.get("model") is None
                or isinstance(confidence, bool) or not isinstance(confidence, (int, float))
                or not threshold < confidence <= 1
                or assessment.get("authenticity") != "UNVERIFIED"
                or assessment.get("visual_signals")):
            continue
        if require_self_review and (
            self_review.get("status") != "COMPLETED"
            or self_review.get("confirmed") is not True
            or isinstance(self_confidence, bool)
            or not isinstance(self_confidence, (int, float))
            or not threshold < self_confidence <= 1
            or self_review.get("issues")
            or self_review.get("model") is None
        ):
            continue
        criterion = file.claim.criterion
        claim = file.claim
        if (claim.self_score is None or claim.self_score <= 0
                or assessment.get("criterion_code") != criterion.code
                or (criterion.rule_config or {}).get("mandatory_bcs_review_if_positive")
                or criterion.code in {"8a", "8b", "8c"}):
            continue
        if any(
            finding.get("level") in {"FLAGGED", "UNKNOWN"} and (
                not finding.get("criterion_id") and not finding.get("evidence_file_ids")
                or finding.get("criterion_id") == criterion.id
                or file_id in finding.get("evidence_file_ids", [])
            )
            for finding in rule_checks.get("findings", [])
        ):
            continue

        facts = read.get("facts", [])
        cited = assessment.get("citations", [])
        if not isinstance(facts, list) or not isinstance(cited, list):
            continue
        if not all(isinstance(item, dict) and item in facts for item in cited):
            continue
        cited_kinds = {item.get("kind") for item in cited}
        if not REQUIRED_FACT_KINDS.issubset(cited_kinds):
            continue
        if _person_key(case.student.full_name) not in {
            _person_key(item.get("value", "")) for item in cited if item.get("kind") == "recipient"
        }:
            continue
        accepted.append({
            "evidence_file_id": file_id,
            "sha256": sha,
            "version_no": file.version_no,
            "criterion_id": criterion.id,
            "criterion_code": criterion.code,
            "run_id": run.id,
            "confidence": confidence,
            "self_confidence": self_confidence if require_self_review else None,
            "threshold": threshold,
            "model": assessment["model"],
            "prompt_version": assessment.get("prompt_version"),
            "status": "AUTO_ACCEPTED_PENDING_BCS_SCORE",
        })
    return accepted


def current_auto_accepted(db: Session, case: Case) -> list[dict]:
    """Ignore old decisions after any rubric, self-score, term or file change."""
    from api.app.services.ai_review_service import PIPELINE_VERSION, build_case_snapshot

    threshold = settings.AI_AUTO_ACCEPT_THRESHOLD
    if not settings.AI_AUTO_ACCEPT_ENABLED or not 0 <= threshold <= 1:
        return []
    run = (db.query(AiReviewRun).filter(AiReviewRun.case_id == case.id)
           .order_by(AiReviewRun.created_at.desc(), AiReviewRun.id.desc()).first())
    if (not run or run.status not in {"COMPLETED", "NEEDS_HUMAN"}
            or (run.result_json or {}).get("pipeline_version") != PIPELINE_VERSION):
        return []
    rubric, fingerprint, snapshot = build_case_snapshot(db, case)
    if run.rubric_version != rubric or run.evidence_fingerprint != fingerprint:
        return []
    old_snapshot = dict(run.snapshot_json or {})
    old_snapshot.pop("case_version", None)
    snapshot.pop("case_version", None)
    if old_snapshot != snapshot:
        return []
    return [item for item in (run.result_json or {}).get("auto_accepted_evidence", [])
            if item.get("run_id") == run.id
            and isinstance(item.get("confidence"), (int, float))
            and not isinstance(item.get("confidence"), bool)
            and threshold < item["confidence"] <= 1
            and isinstance(item.get("self_confidence"), (int, float))
            and not isinstance(item.get("self_confidence"), bool)
            and threshold < item["self_confidence"] <= 1]
