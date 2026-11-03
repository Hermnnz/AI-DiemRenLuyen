"""Submission-to-AI integration; every provider call is mocked."""

import hashlib
from datetime import date

import pytest
from sqlalchemy.orm import sessionmaker

from api.app.config import settings
from api.app.models.entities import AiReviewRun, Claim, EvidenceFile
from api.tests.conftest import login_helper


@pytest.fixture
def automatic_submission(seed_data, db, monkeypatch):
    case = seed_data["cases"][0]
    campaign = seed_data["campaign"]
    campaign.template_code = "49K14_1_V1"
    campaign.term_start_on = date(2026, 1, 1)
    campaign.term_end_on = date(2026, 12, 31)
    claims = db.query(Claim).filter(Claim.case_id == case.id).all()
    for claim in claims:
        claim.self_score = 0
    claim = next(item for item in claims if item.criterion_id == seed_data["criteria"][0].id)
    claim.self_score = 1
    data = b"mocked-submitted-evidence"
    evidence = EvidenceFile(
        claim_id=claim.id, storage_key="automatic.png", original_name="automatic.png",
        mime_type="image/png", size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
        uploaded_by=case.student_id, version_no=1, is_current=True,
    )
    db.add(evidence)
    db.commit()
    facts = [{"kind": kind, "value": value, "page": 1, "source_excerpt": value}
             for kind, value in [("recipient", case.student.full_name),
                                 ("activity_name", "Hội thảo A"),
                                 ("event_date", "2026-10-15"), ("issuer", "Đoàn trường")]]
    options = {"confidence": 0.70, "self_confidence": 0.70, "verdict": "SUPPORTED"}
    calls = []

    async def read(self, evidence_file_id, sha256, mime_type, content):
        calls.append("read")
        return {"evidence_file_id": evidence_file_id, "sha256": sha256,
                "readable": True, "unreadable_reason": "", "facts": facts}

    async def assess(self, **kwargs):
        calls.append("assess")
        return {"evidence_file_id": evidence.id, "sha256": evidence.sha256,
                "criterion_code": kwargs["criterion"]["code"],
                "rule_clause_id": "49K14_1_V1:TC01", "rule_text": "Demo",
                "evidence_requirements": "", "verdict": options["verdict"],
                "raw_verdict": options["verdict"], "confidence": options["confidence"],
                "reason": "Kết quả mock", "citations": list(facts),
                "visual_signals": [], "authenticity": "UNVERIFIED", "limitations": [],
                "requires_human_review": True, "model": self.model, "prompt_version": "mock"}

    async def self_review(self, **kwargs):
        calls.append("self_review")
        if options.get("limit_self_once") and calls.count("self_review") == 1:
            from api.app.review.gemini_read import GeminiReadError
            raise GeminiReadError("MODEL_RATE_LIMITED", retryable=True)
        return {"status": "COMPLETED", "confirmed": True,
                "confidence": options["self_confidence"], "issues": [], "reason": "Mock",
                "model": self.model, "prompt_version": "mock"}

    for key, value in {"AI_READ_ENABLED": True, "AI_TRANSPARENCY_ENABLED": True,
                       "AI_AUTO_ACCEPT_ENABLED": True, "AI_AUTO_ACCEPT_THRESHOLD": 0.70,
                       "GEMINI_API_KEY": "mock-only"}.items():
        monkeypatch.setattr(settings, key, value)
    monkeypatch.setattr("api.app.services.ai_review_service._load_evidence_bytes", lambda _: data)
    monkeypatch.setattr("api.app.services.ai_review_service.GeminiReadProvider.read", read)
    monkeypatch.setattr("api.app.services.ai_review_service.GeminiTransparencyProvider.assess", assess)
    monkeypatch.setattr("api.app.services.ai_review_service.GeminiTransparencyProvider.self_review", self_review)
    # Background work deliberately uses a different session from the request.
    monkeypatch.setattr("api.app.services.ai_review_dispatch.SessionLocal", sessionmaker(bind=db.get_bind()))
    return case, evidence, facts, options, calls


@pytest.mark.parametrize("mode,accepted", [
    ("at_threshold", True), ("primary_75", True), ("self_review_75", True), ("low_primary", False),
    ("low_self_review", False), ("flagged", False), ("wrong_recipient", False),
])
def test_submission_runs_ai_without_bcs_click(client, db, automatic_submission, mode, accepted):
    case, evidence, facts, options, calls = automatic_submission
    if mode == "primary_75":
        options["confidence"] = 0.75
    elif mode == "self_review_75":
        options["self_confidence"] = 0.75
    elif mode == "low_primary":
        options["confidence"] = 0.6999
    elif mode == "low_self_review":
        options["self_confidence"] = 0.6999
    elif mode == "flagged":
        options["verdict"] = "FLAGGED"
    elif mode == "wrong_recipient":
        facts[0] = {**facts[0], "value": "Người khác", "source_excerpt": "Người khác"}
    student = login_helper(client, "sv001")
    payload = {"expected_version": case.version}
    response = client.post(f"/api/v1/student/cases/{case.id}/submit", json=payload,
                           cookies=student["cookies"], headers=student["headers"])
    assert response.status_code == 200
    assert response.json()["status"] == "BCS_REVIEW"
    db.expire_all()
    run = db.query(AiReviewRun).filter_by(case_id=case.id).one()
    assert run.status == "NEEDS_HUMAN"  # BCS still owns the final score.
    assert run.case_version == case.version
    assert bool(run.result_json["auto_accepted_evidence"]) is accepted
    if accepted:
        decision = run.result_json["auto_accepted_evidence"][0]
        assert decision["threshold"] == 0.70
        assert decision["confidence"] >= 0.70 and decision["self_confidence"] >= 0.70
    assert calls[:2] == ["read", "assess"]
    bcs = login_helper(client, "bcs001")
    detail = client.get(f"/api/v1/bcs/cases/{case.id}", cookies=bcs["cookies"]).json()
    assert (evidence.id not in detail["evidence_review_required_ids"]) is accepted
    assert all(item.approved_score is None for item in db.query(Claim).filter_by(case_id=case.id))
    assert case.proposed_total is None
    request_count = len(calls)
    assert client.post(f"/api/v1/student/cases/{case.id}/submit", json=payload,
                       cookies=student["cookies"], headers=student["headers"]).status_code == 409
    assert db.query(AiReviewRun).filter_by(case_id=case.id).count() == 1
    assert len(calls) == request_count


def test_missing_evidence_does_not_start_ai(client, db, automatic_submission):
    case, evidence, _, _, calls = automatic_submission
    db.delete(evidence)
    db.commit()
    student = login_helper(client, "sv001")
    response = client.post(f"/api/v1/student/cases/{case.id}/submit",
                           json={"expected_version": case.version},
                           cookies=student["cookies"], headers=student["headers"])
    assert response.json()["status"] == "NEEDS_INFO"
    assert db.query(AiReviewRun).filter_by(case_id=case.id).count() == 0
    assert calls == []


def test_old_submission_is_dispatched_automatically_on_open(client, db, automatic_submission):
    case, evidence, _, _, calls = automatic_submission
    case.status = "BCS_REVIEW"
    db.commit()
    bcs = login_helper(client, "bcs001")
    path = f"/api/v1/bcs/cases/{case.id}/ai-reviews/latest"
    assert client.get(path, cookies=bcs["cookies"]).json()["run"]["status"] == "QUEUED"
    db.expire_all()
    run = db.query(AiReviewRun).filter_by(case_id=case.id).one()
    assert run.result_json["auto_accepted_evidence"][0]["evidence_file_id"] == evidence.id
    assert client.get(path, cookies=bcs["cookies"]).json()["run"]["status"] == "NEEDS_HUMAN"
    assert calls == ["read", "assess", "self_review"]


def test_submit_and_queue_share_transaction(db, automatic_submission, monkeypatch):
    from datetime import datetime, timezone
    from api.app.services.workflow_service import submit_student_case

    case, _, _, _, calls = automatic_submission
    def forbid_commit():
        raise AssertionError("Submission service must not commit before its caller")
    monkeypatch.setattr(db, "commit", forbid_commit)
    submitted, _ = submit_student_case(db, case, case.student, case.version, datetime.now(timezone.utc))
    run = db.query(AiReviewRun).filter_by(case_id=case.id).one()
    assert run.status == "QUEUED"
    assert run.case_version == submitted.version
    assert calls == []


def test_automatic_worker_failure_does_not_fail_submission(client, db, automatic_submission, monkeypatch):
    from api.app.review.gemini_read import GeminiReadError

    case, evidence, _, _, _ = automatic_submission
    async def bad_read(self, *_args):
        raise GeminiReadError("MODEL_RESPONSE_INVALID", retryable=False)
    monkeypatch.setattr("api.app.services.ai_review_service.GeminiReadProvider.read", bad_read)
    student = login_helper(client, "sv001")
    response = client.post(f"/api/v1/student/cases/{case.id}/submit",
                           json={"expected_version": case.version},
                           cookies=student["cookies"], headers=student["headers"])
    assert response.status_code == 200
    db.expire_all()
    run = db.query(AiReviewRun).filter_by(case_id=case.id).one()
    assert run.error_code == "MODEL_RESPONSE_INVALID"
    assert run.status == "NEEDS_HUMAN"
    assert case.status == "BCS_REVIEW"
    bcs = login_helper(client, "bcs001")
    detail = client.get(f"/api/v1/bcs/cases/{case.id}", cookies=bcs["cookies"]).json()
    assert evidence.id in detail["evidence_review_required_ids"]


def test_automatic_retry_keeps_backoff_and_cached_primary(client, db, automatic_submission, monkeypatch):
    from datetime import datetime, timedelta

    case, evidence, _, options, calls = automatic_submission
    options["limit_self_once"] = True
    waits = []
    async def advance_retry_clock(delay):
        waits.append(delay)
        with sessionmaker(bind=db.get_bind())() as worker_db:
            run = worker_db.query(AiReviewRun).filter_by(case_id=case.id).one()
            assert run.error_code == "MODEL_RATE_LIMITED"
            assert run.attempt_count == 1
            run.lease_until = datetime.utcnow() - timedelta(seconds=1)
            worker_db.commit()
    monkeypatch.setattr("api.app.services.ai_review_dispatch.sleep", advance_retry_clock)
    student = login_helper(client, "sv001")
    response = client.post(f"/api/v1/student/cases/{case.id}/submit",
                           json={"expected_version": case.version},
                           cookies=student["cookies"], headers=student["headers"])
    assert response.status_code == 200
    db.expire_all()
    run = db.query(AiReviewRun).filter_by(case_id=case.id).one()
    assert len(waits) == 1 and 0 < waits[0] <= 60
    assert calls == ["read", "assess", "self_review", "self_review"]
    assert run.attempt_count == 2 and run.error_code is None
    assert run.result_json["auto_accepted_evidence"][0]["evidence_file_id"] == evidence.id


def test_submit_rollback_also_removes_queued_job(db, automatic_submission):
    from datetime import datetime, timezone
    from api.app.services.workflow_service import submit_student_case

    case, _, _, _, calls = automatic_submission
    savepoint = db.begin_nested()
    submit_student_case(db, case, case.student, case.version, datetime.now(timezone.utc))
    assert db.query(AiReviewRun).filter_by(case_id=case.id).count() == 1
    savepoint.rollback()
    db.expire_all()
    assert case.status == "DRAFT"
    assert db.query(AiReviewRun).filter_by(case_id=case.id).count() == 0
    assert calls == []


def test_automatic_review_respects_postgres_prompt_version_limit(client, db, automatic_submission):
    from sqlalchemy import event
    from sqlalchemy.orm import Session
    from api.app.services.ai_review_service import _prompt_versions

    case, _, _, _, calls = automatic_submission
    observed = []
    def enforce_varchar_limit(session, _context, _instances):
        for instance in session.new.union(session.dirty):
            if isinstance(instance, AiReviewRun) and instance.prompt_version:
                observed.append(instance.prompt_version)
                assert len(instance.prompt_version) <= AiReviewRun.__table__.c.prompt_version.type.length
    event.listen(Session, "before_flush", enforce_varchar_limit)
    try:
        student = login_helper(client, "sv001")
        response = client.post(f"/api/v1/student/cases/{case.id}/submit",
                               json={"expected_version": case.version}, cookies=student["cookies"], headers=student["headers"])
        assert response.status_code == 200
    finally:
        event.remove(Session, "before_flush", enforce_varchar_limit)
    db.expire_all()
    run = db.query(AiReviewRun).filter_by(case_id=case.id).one()
    assert observed and run.error_code is None
    assert calls == ["read", "assess", "self_review"]
    assert run.prompt_version.startswith("ai-prompts:")
    assert run.result_json["prompt_versions"] == _prompt_versions()
    assert run.result_json["auto_accepted_evidence"]


def test_compact_prompt_identity_changes_with_any_component_version(monkeypatch):
    from api.app.services import ai_review_service as service

    baseline = service._combined_prompt_version()
    for name in ("PROMPT_VERSION", "TRANSPARENCY_PROMPT_VERSION", "SELF_REVIEW_PROMPT_VERSION"):
        with monkeypatch.context() as patch:
            patch.setattr(service, name, getattr(service, name) + "-new")
            assert service._combined_prompt_version() != baseline
            assert len(service._combined_prompt_version()) <= 50
