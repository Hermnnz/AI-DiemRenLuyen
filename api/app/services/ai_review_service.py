"""Durable review queue for deterministic checks and optional AI reading."""

import hashlib
import json
import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from api.app.models.entities import AiAgentStep, AiReviewRun, Campaign, Case, Claim, Criterion, EvidenceFile
from api.app.config import settings
from api.app.review.gemini_read import GeminiReadError, GeminiReadProvider, PROMPT_VERSION
from api.app.review.gemini_transparency import GeminiTransparencyProvider, PROMPT_VERSION as TRANSPARENCY_PROMPT_VERSION
from api.app.review.provider import ManualReviewProvider
from api.app.schemas.common import AppError, format_datetime
from api.app.services.audit_service import log_audit
from api.app.services.file_service import get_file_path
from api.app.services.remote_storage import download_object, remote_storage_enabled
from api.app.services.rule_check_service import RULE_VERSION, evaluate_case_rules
from api.app.services.score_decision_service import DECISION_VERSION, evaluate_score_suggestions
from api.app.services.auto_evidence_service import select_auto_accepted


PIPELINE_VERSION = "gemini-read-transparency-decision-v2"


class StaleReview(Exception):
    pass
def _digest(data: object) -> str:
    encoded = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_case_snapshot(db: Session, case: Case) -> tuple[str, str, dict]:
    campaign = db.query(Campaign).filter(Campaign.id == case.campaign_id).one()
    criteria = (
        db.query(Criterion)
        .filter(Criterion.campaign_id == campaign.id)
        .order_by(Criterion.sort_order, Criterion.code)
        .all()
    )
    claims = db.query(Claim).filter(Claim.case_id == case.id).all()
    claim_ids = [claim.id for claim in claims]
    evidence = (
        db.query(EvidenceFile)
        .filter(EvidenceFile.claim_id.in_(claim_ids), EvidenceFile.is_current.is_(True))
        .all()
        if claim_ids else []
    )
    rubric_items = [
        {
            "id": criterion.id,
            "code": criterion.code,
            "max_score": str(criterion.max_score),
            "title": criterion.title,
            "description": criterion.description,
            "requires_evidence": criterion.requires_evidence,
            "evidence_notes": criterion.evidence_notes,
            "rule_config": criterion.rule_config,
        }
        for criterion in criteria
    ]
    rubric_version = f"{campaign.template_code or 'LEGACY_DEMO'}:{_digest(rubric_items)[:12]}"
    evidence_items = sorted(
        (
            {"id": item.id, "claim_id": item.claim_id, "sha256": item.sha256, "version_no": item.version_no}
            for item in evidence
        ),
        key=lambda item: item["id"],
    )
    snapshot = {
        "case_id": case.id,
        "case_version": case.version,
        "rubric_version": rubric_version,
        "term_start_on": campaign.term_start_on.isoformat() if campaign.term_start_on else None,
        "term_end_on": campaign.term_end_on.isoformat() if campaign.term_end_on else None,
        "claims": sorted(
            ({"id": claim.id, "criterion_id": claim.criterion_id, "self_score": str(claim.self_score) if claim.self_score is not None else None}
             for claim in claims),
            key=lambda item: item["id"],
        ),
        "evidence": evidence_items,
    }
    return rubric_version, _digest(evidence_items), snapshot


def enqueue_ai_review(db: Session, case: Case, requested_by: str) -> AiReviewRun:
    if case.status != "BCS_REVIEW":
        raise AppError(status_code=409, code="INVALID_STATE", message="Chỉ phân tích AI khi hồ sơ đang chờ Ban cán sự xem xét.")
    rubric_version, evidence_fingerprint, snapshot = build_case_snapshot(db, case)
    idempotency_key = _digest([case.id, case.version, rubric_version, evidence_fingerprint,
                               PIPELINE_VERSION, RULE_VERSION, DECISION_VERSION,
                               PROMPT_VERSION, TRANSPARENCY_PROMPT_VERSION, settings.GEMINI_MODEL,
                               settings.GEMINI_TRANSPARENCY_MODEL,
                               settings.AI_READ_ENABLED, settings.AI_TRANSPARENCY_ENABLED,
                               settings.AI_AUTO_ACCEPT_ENABLED, settings.AI_AUTO_ACCEPT_THRESHOLD])
    existing = db.query(AiReviewRun).filter(AiReviewRun.idempotency_key == idempotency_key).first()
    if existing:
        return existing

    run = AiReviewRun(
        case_id=case.id,
        requested_by=requested_by,
        case_version=case.version,
        rubric_version=rubric_version,
        evidence_fingerprint=evidence_fingerprint,
        idempotency_key=idempotency_key,
        snapshot_json=snapshot,
        result_json={"rule_checks": evaluate_case_rules(db, case)},
        status="QUEUED",
        created_at=datetime.now(timezone.utc),
    )
    run.steps = [
        AiAgentStep(kind="AI_READ", sort_order=1, status="PENDING"),
        AiAgentStep(kind="AI_TRANSPARENCY", sort_order=2, status="PENDING"),
    ]
    run.result_json["score_suggestions"] = evaluate_score_suggestions(
        db, case, rule_checks=run.result_json["rule_checks"],
        rubric_version=rubric_version, source_run_id=run.id,
    )
    try:
        with db.begin_nested():
            db.add(run)
            db.flush()
    except IntegrityError:
        return db.query(AiReviewRun).filter(AiReviewRun.idempotency_key == idempotency_key).one()

    log_audit(db, campaign_id=case.campaign_id, case_id=case.id, action="AI_REVIEW_QUEUED",
              actor_user_id=requested_by, after_json={"run_id": run.id, "case_version": case.version})
    db.commit()
    return run


def is_stale(db: Session, run: AiReviewRun) -> bool:
    case = db.query(Case).filter(Case.id == run.case_id).first()
    if not case:
        return True
    rubric_version, evidence_fingerprint, snapshot = build_case_snapshot(db, case)
    if run.status in {"COMPLETED", "NEEDS_HUMAN"}:
        # A BCS score/evidence decision increments the case version without
        # changing the evidence the completed model actually examined.
        snapshot.pop("case_version", None)
        original = dict(run.snapshot_json or {})
        original.pop("case_version", None)
    else:
        original = run.snapshot_json
    return (
        (case.version != run.case_version and run.status not in {"COMPLETED", "NEEDS_HUMAN"})
        or
        rubric_version != run.rubric_version
        or evidence_fingerprint != run.evidence_fingerprint
        or snapshot != original
    )


def serialize_run(db: Session, run: AiReviewRun) -> dict:
    return {
        "id": run.id,
        "case_id": run.case_id,
        "case_version": run.case_version,
        "rubric_version": run.rubric_version,
        "status": run.status,
        "stale": is_stale(db, run),
        "attempt_count": run.attempt_count,
        "provider": run.provider,
        "model": run.model,
        "prompt_version": run.prompt_version,
        "result": run.result_json,
        "error_code": run.error_code,
        "created_at": format_datetime(run.created_at),
        "started_at": format_datetime(run.started_at),
        "finished_at": format_datetime(run.finished_at),
        "steps": [
            {"kind": step.kind, "status": step.status, "error_code": step.error_code,
             "output": step.output_json}
            for step in sorted(run.steps, key=lambda step: step.sort_order)
        ],
    }


def _load_evidence_bytes(storage_key: str) -> bytes:
    if remote_storage_enabled():
        return download_object(storage_key)
    with open(get_file_path(storage_key), "rb") as file:
        return file.read()


async def _run_read_step(db: Session, run: AiReviewRun) -> list[dict]:
    step = next(item for item in run.steps if item.kind == "AI_READ")
    expected = run.snapshot_json["evidence"]
    if len(expected) > 8:
        raise GeminiReadError("TOO_MANY_EVIDENCE_FILES")
    ids = [item["id"] for item in expected]
    files = (
        db.query(EvidenceFile).join(Claim, EvidenceFile.claim_id == Claim.id)
        .filter(Claim.case_id == run.case_id, EvidenceFile.id.in_(ids), EvidenceFile.is_current.is_(True))
        .all()
        if ids else []
    )
    by_id = {item.id: item for item in files}
    provider = GeminiReadProvider(settings.GEMINI_API_KEY, settings.GEMINI_MODEL)
    results = list((step.output_json or {}).get("files", []))
    cached = {(item["evidence_file_id"], item["sha256"]) for item in results}
    step.status = "RUNNING"
    step.started_at = step.started_at or datetime.now(timezone.utc)
    run.provider = "google-gemini"
    run.model = settings.GEMINI_MODEL
    run.prompt_version = PROMPT_VERSION
    db.commit()

    for snapshot_file in expected:
        if is_stale(db, run):
            raise StaleReview()
        file = by_id.get(snapshot_file["id"])
        if not file or file.sha256 != snapshot_file["sha256"]:
            raise StaleReview()
        if (file.id, file.sha256) in cached:
            continue
        file_id, file_sha256, file_mime, storage_key = file.id, file.sha256, file.mime_type, file.storage_key
        db.commit()  # Release the read transaction before storage/model I/O.
        data = await asyncio.to_thread(_load_evidence_bytes, storage_key)
        result = await provider.read(file_id, file_sha256, file_mime, data)
        if is_stale(db, run):
            raise StaleReview()
        results.append(result)
        step.output_json = {"files": list(results)}
        db.commit()

    step.status = "COMPLETED"
    step.error_code = None
    step.finished_at = datetime.now(timezone.utc)
    db.commit()
    return results


async def _run_transparency_step(db: Session, run: AiReviewRun, read_results: list[dict]) -> list[dict]:
    step = next(item for item in run.steps if item.kind == "AI_TRANSPARENCY")
    case = db.query(Case).filter(Case.id == run.case_id).one()
    campaign = db.query(Campaign).filter(Campaign.id == case.campaign_id).one()
    claims = {item.id: item for item in db.query(Claim).filter(Claim.case_id == case.id).all()}
    criteria = {item.id: item for item in db.query(Criterion).filter(Criterion.campaign_id == case.campaign_id).all()}
    expected = run.snapshot_json["evidence"]
    file_ids = [item["id"] for item in expected]
    files = (
        db.query(EvidenceFile).join(Claim, EvidenceFile.claim_id == Claim.id)
        .filter(Claim.case_id == case.id, EvidenceFile.id.in_(file_ids), EvidenceFile.is_current.is_(True))
        .all()
        if file_ids else []
    )
    by_id = {item.id: item for item in files}
    reads = {(item["evidence_file_id"], item["sha256"]): item for item in read_results}
    results = list((step.output_json or {}).get("assessments", []))
    cached = {(item["evidence_file_id"], item.get("sha256")) for item in results if item.get("evidence_file_id")}
    provider = GeminiTransparencyProvider(settings.GEMINI_API_KEY, settings.GEMINI_TRANSPARENCY_MODEL)
    step.status = "RUNNING"
    step.started_at = step.started_at or datetime.now(timezone.utc)
    run.model = f"{settings.GEMINI_MODEL} + {settings.GEMINI_TRANSPARENCY_MODEL}"
    run.prompt_version = f"{PROMPT_VERSION} + {TRANSPARENCY_PROMPT_VERSION}"
    db.commit()

    for snapshot_file in expected:
        if is_stale(db, run):
            raise StaleReview()
        file = by_id.get(snapshot_file["id"])
        if not file or file.sha256 != snapshot_file["sha256"]:
            raise StaleReview()
        if (file.id, file.sha256) in cached:
            continue
        claim = claims.get(file.claim_id)
        criterion = criteria.get(claim.criterion_id) if claim else None
        if not claim or not criterion or claim.self_score is None or claim.self_score <= 0:
            continue

        clause_id = f"{campaign.template_code}:{criterion.code}"
        read = reads.get((file.id, file.sha256))
        if (campaign.template_code in {None, "LEGACY_DEMO"} or not read or not read.get("readable")
                or not (criterion.description or criterion.evidence_notes)):
            result = {
                "evidence_file_id": file.id, "sha256": file.sha256,
                "criterion_code": criterion.code, "rule_clause_id": clause_id,
                "rule_text": criterion.description or "",
                "evidence_requirements": criterion.evidence_notes or "",
                "verdict": "UNKNOWN", "reason": "Chưa đủ dữ kiện đọc được hoặc điều khoản để đối chiếu.",
                "citations": [], "visual_signals": [], "authenticity": "UNVERIFIED",
                "limitations": ["Ban cán sự cần xem tệp gốc và quy chế."],
                "requires_human_review": True, "model": None, "prompt_version": TRANSPARENCY_PROMPT_VERSION,
            }
        else:
            context = {
                "code": criterion.code, "title": criterion.title,
                "description": criterion.description or "", "evidence_notes": criterion.evidence_notes or "",
                "rule_config": criterion.rule_config or {}, "clause_id": clause_id,
            }
            file_id, file_sha256, file_mime, storage_key = file.id, file.sha256, file.mime_type, file.storage_key
            db.commit()  # No transaction is held while loading evidence or calling Gemini.
            data = await asyncio.to_thread(_load_evidence_bytes, storage_key)
            result = await provider.assess(
                evidence_file_id=file_id, sha256=file_sha256, mime_type=file_mime,
                data=data, read_result=read, criterion=context,
                student_name=case.student.full_name, term=campaign.term,
            )
            if is_stale(db, run):
                raise StaleReview()
        results.append(result)
        step.output_json = {"assessments": list(results)}
        db.commit()

    step.status = "COMPLETED"
    step.error_code = None
    step.finished_at = datetime.now(timezone.utc)
    db.commit()
    return results


async def run_ai_tick(db: Session, limit: int = 1, target_run_id: str | None = None) -> dict:
    """Process a bounded queue batch; model I/O never holds a DB transaction."""
    processed = stale = needs_human = failed = 0
    for _ in range(limit):
        now = datetime.utcnow()
        query = db.query(AiReviewRun)
        if target_run_id:
            query = query.filter(AiReviewRun.id == target_run_id)
        run = (
            query
            .filter(or_(
                and_(AiReviewRun.status == "QUEUED",
                     or_(AiReviewRun.lease_until.is_(None), AiReviewRun.lease_until < now)),
                and_(AiReviewRun.status == "RUNNING", AiReviewRun.lease_until < now),
            ))
            .order_by(AiReviewRun.created_at, AiReviewRun.id)
            .with_for_update(skip_locked=True)
            .first()
        )
        if not run:
            break
        run_id = run.id
        run.status = "RUNNING"
        run.started_at = now
        run.lease_until = now + timedelta(minutes=15)
        run.attempt_count += 1
        db.commit()  # Never hold a database transaction while invoking a model.

        try:
            if is_stale(db, run):
                raise StaleReview()
            if not settings.AI_READ_ENABLED or not settings.GEMINI_API_KEY:
                manual = ManualReviewProvider().review(run.case_id)
                run.status = "NEEDS_HUMAN"
                run.result_json = {**manual.model_dump(), "rule_checks": (run.result_json or {}).get("rule_checks")}
                run.result_json["score_suggestions"] = evaluate_score_suggestions(
                    db, db.query(Case).filter(Case.id == run.case_id).one(),
                    rule_checks=run.result_json["rule_checks"], rubric_version=run.rubric_version,
                    source_run_id=run.id,
                )
                for step in run.steps:
                    step.status = "SKIPPED"
                    step.error_code = "MODEL_NOT_CONFIGURED"
                    step.finished_at = datetime.now(timezone.utc)
            else:
                read_results = await _run_read_step(db, run)
                transparency = next(item for item in run.steps if item.kind == "AI_TRANSPARENCY")
                assessments = []
                if settings.AI_TRANSPARENCY_ENABLED:
                    assessments = await _run_transparency_step(db, run, read_results)
                else:
                    transparency.status = "SKIPPED"
                    transparency.error_code = "MODEL_NOT_ENABLED"
                    transparency.finished_at = datetime.now(timezone.utc)
                run.status = "NEEDS_HUMAN"
                case = db.query(Case).filter(Case.id == run.case_id).one()
                rule_checks = evaluate_case_rules(db, case, read_results)
                auto_accepted = select_auto_accepted(db, case, run, read_results, assessments, rule_checks)
                run.result_json = {
                    "mode": "AI_READ_AND_TRANSPARENCY" if settings.AI_TRANSPARENCY_ENABLED else "AI_READ_ONLY",
                    "needs_human_review": True,
                    "summary": ("Đã đọc và đối chiếu minh chứng. Ban cán sự cần kiểm tra nguồn và chốt kết quả."
                                if settings.AI_TRANSPARENCY_ENABLED else
                                "Đã trích dữ kiện từ minh chứng. Ban cán sự cần kiểm tra nguồn và tự đối chiếu quy tắc."),
                    "findings": {"read": read_results, "transparency": assessments},
                    "auto_accepted_evidence": auto_accepted,
                    "auto_accept_threshold": settings.AI_AUTO_ACCEPT_THRESHOLD,
                    "rule_checks": rule_checks,
                    "score_suggestions": evaluate_score_suggestions(
                        db, case, assessments=assessments, rule_checks=rule_checks,
                        rubric_version=run.rubric_version, source_run_id=run.id,
                    ),
                }
            needs_human += 1
            run.finished_at = datetime.now(timezone.utc)
            run.lease_until = None
            case = db.query(Case).filter(Case.id == run.case_id).one()
            log_audit(db, campaign_id=case.campaign_id, case_id=case.id, action="AI_REVIEW_FINISHED",
                      after_json={"run_id": run.id, "status": run.status,
                                  "auto_accepted_evidence_file_ids": [item["evidence_file_id"] for item in
                                                                       (run.result_json or {}).get("auto_accepted_evidence", [])]})
            db.commit()
        except StaleReview:
            run = db.query(AiReviewRun).filter(AiReviewRun.id == run_id).one()
            run.status = "STALE"
            run.error_code = "CASE_CHANGED"
            run.lease_until = None
            run.finished_at = datetime.now(timezone.utc)
            stale += 1
            db.commit()
        except Exception as exc:
            if not isinstance(exc, GeminiReadError):
                db.rollback()
            run = db.query(AiReviewRun).filter(AiReviewRun.id == run_id).one()
            retryable = isinstance(exc, GeminiReadError) and exc.retryable and run.attempt_count < 3
            run.status = "QUEUED" if retryable else "NEEDS_HUMAN"
            run.error_code = exc.code if isinstance(exc, GeminiReadError) else "REVIEW_PROCESSING_FAILED"
            run.lease_until = datetime.utcnow() + timedelta(minutes=run.attempt_count) if retryable else None
            run.finished_at = None if retryable else datetime.now(timezone.utc)
            if not retryable:
                run.result_json = {**ManualReviewProvider().review(run.case_id).model_dump(),
                                   "rule_checks": (run.result_json or {}).get("rule_checks")}
                run.result_json["score_suggestions"] = evaluate_score_suggestions(
                    db, db.query(Case).filter(Case.id == run.case_id).one(),
                    rule_checks=run.result_json["rule_checks"], rubric_version=run.rubric_version,
                    source_run_id=run.id,
                )
                needs_human += 1
            for step in run.steps:
                if step.status == "RUNNING":
                    step.status = "PENDING" if retryable else "FAILED"
                    step.error_code = run.error_code
            failed += 1
            db.commit()
        processed += 1
    return {"processed": processed, "needs_human": needs_human, "stale": stale, "failed": failed}
