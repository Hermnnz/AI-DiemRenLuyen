from api.app.config import settings
from api.app.review.gemini_read import GeminiReadError
import hashlib

from api.app.models.entities import AiReviewRun, Claim, EvidenceFile
from api.app.services.auto_evidence_service import select_auto_accepted
from api.tests.conftest import login_helper


def test_bcs_can_enqueue_idempotent_review_and_manual_tick(client, seed_data, db, monkeypatch):
    case = seed_data["cases"][0]
    case.status = "BCS_REVIEW"
    db.commit()
    bcs = login_helper(client, "bcs001")
    path = f"/api/v1/bcs/cases/{case.id}/ai-reviews"

    assert client.get(path + "/latest", cookies=bcs["cookies"]).json() == {"run": None}
    first = client.post(path, cookies=bcs["cookies"], headers=bcs["headers"])
    assert first.status_code == 202
    run = first.json()
    assert run["status"] == "QUEUED"
    assert [step["kind"] for step in run["steps"]] == ["AI_READ", "AI_TRANSPARENCY"]
    assert client.post(path, cookies=bcs["cookies"], headers=bcs["headers"]).json()["id"] == run["id"]
    assert db.query(AiReviewRun).filter(AiReviewRun.case_id == case.id).count() == 1

    student = login_helper(client, "sv001")
    assert client.post(path, cookies=student["cookies"], headers=student["headers"]).status_code == 403
    other_bcs = login_helper(client, "bcs_other")
    assert client.get(path + "/latest", cookies=other_bcs["cookies"]).status_code == 403

    monkeypatch.setattr(settings, "CRON_SECRET", "test-ai-cron")
    assert client.post("/api/v1/internal/ai-tick").status_code == 401
    tick = client.post("/api/v1/internal/ai-tick", headers={"Authorization": "Bearer test-ai-cron"})
    assert tick.status_code == 200
    assert tick.json()["needs_human"] == 1
    latest = client.get(path + "/latest", cookies=bcs["cookies"]).json()["run"]
    assert latest["status"] == "NEEDS_HUMAN"
    assert latest["result"]["mode"] == "MANUAL"
    assert latest["result"]["rule_checks"]["case_id"] == case.id
    assert latest["result"]["score_suggestions"]["case_id"] == case.id
    assert latest["result"]["score_suggestions"]["requires_bcs_approval"] is True
    assert [step["status"] for step in latest["steps"]] == ["SKIPPED", "SKIPPED"]
    assert client.get(path + f"/{run['id']}", cookies=bcs["cookies"]).status_code == 200
    assert case.status == "BCS_REVIEW"


def test_changed_case_invalidates_queued_review(client, seed_data, db, monkeypatch):
    case = seed_data["cases"][0]
    case.status = "BCS_REVIEW"
    db.commit()
    bcs = login_helper(client, "bcs001")
    path = f"/api/v1/bcs/cases/{case.id}/ai-reviews"
    queued = client.post(path, cookies=bcs["cookies"], headers=bcs["headers"])
    assert queued.status_code == 202

    case.version += 1
    db.commit()
    assert client.get(path + "/latest", cookies=bcs["cookies"]).json()["run"]["stale"] is True
    monkeypatch.setattr(settings, "CRON_SECRET", "test-ai-cron")
    tick = client.post("/api/v1/internal/ai-tick", headers={"Authorization": "Bearer test-ai-cron"})
    assert tick.json()["stale"] == 1
    assert client.get(path + "/latest", cookies=bcs["cookies"]).json()["run"]["status"] == "STALE"

    fresh = client.post(path, cookies=bcs["cookies"], headers=bcs["headers"])
    assert fresh.status_code == 202
    assert fresh.json()["id"] != queued.json()["id"]


def test_gemini_read_worker_keeps_bcs_decision_manual(client, seed_data, db, monkeypatch):
    case = seed_data["cases"][0]
    case.status = "BCS_REVIEW"
    claim = db.query(Claim).filter(Claim.case_id == case.id).first()
    data = b"synthetic-image"
    evidence = EvidenceFile(
        claim_id=claim.id, storage_key="synthetic.png", original_name="synthetic.png",
        mime_type="image/png", size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
        uploaded_by=case.student_id, version_no=1, is_current=True,
    )
    db.add(evidence)
    db.commit()

    async def fake_read(self, evidence_file_id, sha256, mime_type, content):
        assert content == data
        return {"evidence_file_id": evidence_file_id, "sha256": sha256, "readable": True,
                "unreadable_reason": "", "facts": [{"kind": "activity_name", "value": "Hội thảo A",
                                                  "page": 1, "source_excerpt": "Hội thảo A"}]}

    monkeypatch.setattr(settings, "AI_READ_ENABLED", True)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(settings, "CRON_SECRET", "test-ai-cron")
    monkeypatch.setattr("api.app.services.ai_review_service._load_evidence_bytes", lambda _: data)
    monkeypatch.setattr("api.app.services.ai_review_service.GeminiReadProvider.read", fake_read)

    bcs = login_helper(client, "bcs001")
    path = f"/api/v1/bcs/cases/{case.id}/ai-reviews"
    assert client.post(path, cookies=bcs["cookies"], headers=bcs["headers"]).status_code == 202
    response = client.post("/api/v1/internal/ai-tick", headers={"Authorization": "Bearer test-ai-cron"})
    assert response.status_code == 200
    run = client.get(path + "/latest", cookies=bcs["cookies"]).json()["run"]
    assert run["status"] == "NEEDS_HUMAN"
    assert run["result"]["mode"] == "AI_READ_ONLY"
    assert run["result"]["rule_checks"]["date_evidence_status"] == "CHECKED"
    assert run["steps"][0]["status"] == "COMPLETED"
    assert run["steps"][0]["output"]["files"][0]["facts"][0]["source_excerpt"] == "Hội thảo A"
    assert run["steps"][1]["status"] == "SKIPPED"
    assert case.status == "BCS_REVIEW"


def test_rate_limited_run_waits_before_retry(client, seed_data, db, monkeypatch):
    case = seed_data["cases"][0]
    case.status = "BCS_REVIEW"
    claim = db.query(Claim).filter(Claim.case_id == case.id).first()
    data = b"synthetic-image"
    db.add(EvidenceFile(
        claim_id=claim.id, storage_key="rate-limit.png", original_name="rate-limit.png",
        mime_type="image/png", size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
        uploaded_by=case.student_id, version_no=1, is_current=True,
    ))
    db.commit()

    async def limited_read(self, *_args):
        raise GeminiReadError("MODEL_RATE_LIMITED", retryable=True)

    monkeypatch.setattr(settings, "AI_READ_ENABLED", True)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(settings, "CRON_SECRET", "test-ai-cron")
    monkeypatch.setattr("api.app.services.ai_review_service._load_evidence_bytes", lambda _: data)
    monkeypatch.setattr("api.app.services.ai_review_service.GeminiReadProvider.read", limited_read)

    bcs = login_helper(client, "bcs001")
    path = f"/api/v1/bcs/cases/{case.id}/ai-reviews"
    client.post(path, cookies=bcs["cookies"], headers=bcs["headers"])
    tick_path = "/api/v1/internal/ai-tick"
    auth = {"Authorization": "Bearer test-ai-cron"}
    assert client.post(tick_path, headers=auth).json()["failed"] == 1
    assert client.post(tick_path, headers=auth).json()["processed"] == 0
    run = client.get(path + "/latest", cookies=bcs["cookies"]).json()["run"]
    assert run["status"] == "QUEUED"
    assert run["error_code"] == "MODEL_RATE_LIMITED"
    assert run["attempt_count"] == 1


def test_term_window_change_invalidates_rule_snapshot(client, seed_data, db):
    case = seed_data["cases"][0]
    case.status = "BCS_REVIEW"
    db.commit()
    bcs = login_helper(client, "bcs001")
    path = f"/api/v1/bcs/cases/{case.id}/ai-reviews"
    queued = client.post(path, cookies=bcs["cookies"], headers=bcs["headers"])
    assert queued.status_code == 202

    campaign = seed_data["campaign"]
    from datetime import date
    campaign.term_start_on = date(2025, 9, 1)
    campaign.term_end_on = date(2026, 1, 31)
    db.commit()
    latest = client.get(path + "/latest", cookies=bcs["cookies"]).json()["run"]
    assert latest["stale"] is True


def test_transparency_worker_uses_separate_model_and_keeps_bcs_in_control(client, seed_data, db, monkeypatch):
    case = seed_data["cases"][0]
    case.status = "BCS_REVIEW"
    claim = db.query(Claim).filter(Claim.case_id == case.id).first()
    claim.self_score = 1
    seed_data["campaign"].template_code = "49K14_1_V1"
    data = b"synthetic-image"
    evidence = EvidenceFile(
        claim_id=claim.id, storage_key="transparency.png", original_name="transparency.png",
        mime_type="image/png", size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
        uploaded_by=case.student_id, version_no=1, is_current=True,
    )
    db.add(evidence)
    db.commit()

    async def fake_read(self, evidence_file_id, sha256, mime_type, content):
        assert self.model == "gemini-3.5-flash-lite"
        return {"evidence_file_id": evidence_file_id, "sha256": sha256, "readable": True,
                "unreadable_reason": "", "facts": [{"kind": "activity_name", "value": "Hội thảo A",
                                                  "page": 1, "source_excerpt": "Hội thảo A"}]}

    async def fake_assess(self, **kwargs):
        assert self.model == "gemini-3.6-flash"
        assert kwargs["data"] == data
        assert kwargs["read_result"]["facts"][0]["value"] == "Hội thảo A"
        return {"evidence_file_id": evidence.id, "sha256": evidence.sha256,
                "criterion_code": kwargs["criterion"]["code"], "rule_clause_id": "test:criterion",
                "rule_text": "Test rule", "evidence_requirements": "", "verdict": "UNKNOWN",
                "reason": "Cần kiểm tra nguồn cấp.", "citations": [], "visual_signals": [],
                "authenticity": "UNVERIFIED", "limitations": [], "requires_human_review": True,
                "model": self.model, "prompt_version": "ai-transparency-v1"}

    monkeypatch.setattr(settings, "AI_READ_ENABLED", True)
    monkeypatch.setattr(settings, "AI_TRANSPARENCY_ENABLED", True)
    monkeypatch.setattr(settings, "GEMINI_MODEL", "gemini-3.5-flash-lite")
    monkeypatch.setattr(settings, "GEMINI_TRANSPARENCY_MODEL", "gemini-3.6-flash")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(settings, "CRON_SECRET", "test-ai-cron")
    monkeypatch.setattr("api.app.services.ai_review_service._load_evidence_bytes", lambda _: data)
    monkeypatch.setattr("api.app.services.ai_review_service.GeminiReadProvider.read", fake_read)
    monkeypatch.setattr("api.app.services.ai_review_service.GeminiTransparencyProvider.assess", fake_assess)

    bcs = login_helper(client, "bcs001")
    path = f"/api/v1/bcs/cases/{case.id}/ai-reviews"
    assert client.post(path, cookies=bcs["cookies"], headers=bcs["headers"]).status_code == 202
    tick = client.post("/api/v1/internal/ai-tick", headers={"Authorization": "Bearer test-ai-cron"})
    assert tick.status_code == 200
    run = client.get(path + "/latest", cookies=bcs["cookies"]).json()["run"]
    assert run["result"]["mode"] == "AI_READ_AND_TRANSPARENCY"
    assert run["steps"][1]["status"] == "COMPLETED"
    assert run["steps"][1]["output"]["assessments"][0]["verdict"] == "UNKNOWN"
    assert run["result"]["needs_human_review"] is True
    assert case.status == "BCS_REVIEW"


def test_high_confidence_evidence_auto_accepted_and_bcs_override_is_recorded(client, seed_data, db, monkeypatch):
    from datetime import date

    case = seed_data["cases"][0]
    case.status = "BCS_REVIEW"
    claim = db.query(Claim).filter(Claim.case_id == case.id).first()
    claim.self_score = 1
    campaign = seed_data["campaign"]
    campaign.template_code = "49K14_1_V1"
    campaign.term_start_on = date(2026, 1, 1)
    campaign.term_end_on = date(2026, 12, 31)
    data = b"synthetic-evidence"
    evidence = EvidenceFile(
        claim_id=claim.id, storage_key="auto-accepted.png", original_name="auto-accepted.png",
        mime_type="image/png", size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
        uploaded_by=case.student_id, version_no=1, is_current=True,
    )
    db.add(evidence)
    db.commit()

    facts = [
        {"kind": kind, "value": value, "page": 1, "source_excerpt": value}
        for kind, value in [
            ("recipient", case.student.full_name), ("activity_name", "Hội thảo A"),
            ("event_date", "2026-10-15"), ("issuer", "Đoàn trường"),
        ]
    ]

    async def fake_read(self, evidence_file_id, sha256, mime_type, content):
        return {"evidence_file_id": evidence_file_id, "sha256": sha256,
                "readable": True, "unreadable_reason": "", "facts": facts}

    assess_calls = 0
    self_review_calls = 0

    async def fake_assess(self, **kwargs):
        nonlocal assess_calls
        assess_calls += 1
        return {"evidence_file_id": evidence.id, "sha256": evidence.sha256,
                "criterion_code": kwargs["criterion"]["code"], "rule_clause_id": "49K14_1_V1:TC01",
                "rule_text": "Demo", "evidence_requirements": "", "verdict": "SUPPORTED",
                "raw_verdict": "SUPPORTED", "post_processing_reason": None,
                "confidence": 0.91, "reason": "Bốn dữ kiện phù hợp.", "citations": facts,
                "visual_signals": [], "authenticity": "UNVERIFIED", "limitations": ["Chưa xác minh nguồn cấp."],
                "requires_human_review": True, "model": self.model, "prompt_version": "ai-transparency-v2"}

    async def fake_self_review(self, **kwargs):
        nonlocal self_review_calls
        self_review_calls += 1
        assert kwargs["primary_assessment"]["confidence"] == 0.91
        if self_review_calls == 1:
            raise GeminiReadError("MODEL_RATE_LIMITED", retryable=True)
        return {"status": "COMPLETED", "confirmed": True, "confidence": 0.93,
                "reason": "Đã rà soát bốn dữ kiện.", "issues": [],
                "model": self.model, "prompt_version": "ai-transparency-self-review-v1"}

    for key, value in {"AI_READ_ENABLED": True, "AI_TRANSPARENCY_ENABLED": True,
                       "AI_AUTO_ACCEPT_ENABLED": True, "AI_AUTO_ACCEPT_THRESHOLD": 0.85,
                       "GEMINI_API_KEY": "test-key", "CRON_SECRET": "test-ai-cron"}.items():
        monkeypatch.setattr(settings, key, value)
    monkeypatch.setattr("api.app.services.ai_review_service._load_evidence_bytes", lambda _: data)
    monkeypatch.setattr("api.app.services.ai_review_service.GeminiReadProvider.read", fake_read)
    monkeypatch.setattr("api.app.services.ai_review_service.GeminiTransparencyProvider.assess", fake_assess)
    monkeypatch.setattr("api.app.services.ai_review_service.GeminiTransparencyProvider.self_review", fake_self_review)

    bcs = login_helper(client, "bcs001")
    path = f"/api/v1/bcs/cases/{case.id}"
    queued = client.post(path + "/ai-reviews", cookies=bcs["cookies"], headers=bcs["headers"])
    assert queued.status_code == 202
    process_path = path + f"/ai-reviews/{queued.json()['id']}/process"
    other_bcs = login_helper(client, "bcs_other")
    assert client.post(process_path, cookies=other_bcs["cookies"], headers=other_bcs["headers"]).status_code == 403
    first_processing = client.post(process_path, cookies=bcs["cookies"], headers=bcs["headers"])
    assert first_processing.status_code == 200
    assert first_processing.json()["status"] == "QUEUED"
    run = db.query(AiReviewRun).filter(AiReviewRun.case_id == case.id).one()
    assert run.steps[1].output_json["assessments"][0]["confidence"] == 0.91
    from datetime import datetime, timedelta
    run.lease_until = datetime.utcnow() - timedelta(seconds=1)
    db.commit()
    assert client.post(process_path, cookies=bcs["cookies"], headers=bcs["headers"]).status_code == 200
    assert assess_calls == 1
    assert self_review_calls == 2
    detail = client.get(path, cookies=bcs["cookies"]).json()
    assert detail["evidence_review_required_ids"] == []
    assert detail["auto_accepted_evidence"][0]["evidence_file_id"] == evidence.id
    assert detail["auto_accepted_evidence"][0]["confidence"] == 0.91
    assert detail["auto_accepted_evidence"][0]["self_confidence"] == 0.93

    run = db.query(AiReviewRun).filter(AiReviewRun.case_id == case.id).first()
    assessment = run.result_json["findings"]["transparency"][0]
    read = run.result_json["findings"]["read"][0]
    checks = run.result_json["rule_checks"]
    for change in ({"confidence": 0.85}, {"citations": facts[:-1]},
                   {"visual_signals": [{"page": 1, "description": "Mờ", "concern": True}]},
                   {"model": None}, {"self_review": {**assessment["self_review"], "confidence": 0.85}},
                   {"self_review": {**assessment["self_review"], "confirmed": False}},
                   {"self_review": {**assessment["self_review"], "issues": ["Tên không khớp"]}}):
        assert select_auto_accepted(db, case, run, [read], [{**assessment, **change}], checks) == []
    assert select_auto_accepted(db, case, run, [read], [assessment],
                                {**checks, "term_window": {"status": "NOT_CONFIGURED"}}) == []
    monkeypatch.setattr(settings, "AI_AUTO_ACCEPT_THRESHOLD", 0.94)
    assert evidence.id in client.get(path, cookies=bcs["cookies"]).json()["evidence_review_required_ids"]
    monkeypatch.setattr(settings, "AI_AUTO_ACCEPT_THRESHOLD", 0.85)
    original_code = claim.criterion.code
    claim.criterion.code = "8a"
    assert select_auto_accepted(db, case, run, [read], [assessment], checks) == []
    claim.criterion.code = original_code

    rejected = client.put(path + f"/evidence/{evidence.id}/decision",
                          json={"decision": "REJECT_ITEM", "reason": "Tên trên bản gốc không khớp hồ sơ",
                                "expected_version": case.version},
                          cookies=bcs["cookies"], headers=bcs["headers"])
    assert rejected.status_code == 200
    assert client.get(path + "/ai-reviews/latest", cookies=bcs["cookies"]).json()["run"]["stale"] is False
    from api.app.models.entities import BcsAiFeedback
    feedback = db.query(BcsAiFeedback).filter(BcsAiFeedback.evidence_file_id == evidence.id).one()
    assert feedback.ai_run_id == run.id
    assert feedback.ai_verdict == "SUPPORTED"
    assert feedback.bcs_decision == "REJECT_ITEM"
    assert feedback.discrepancy_status == "NEEDS_REVIEW"
