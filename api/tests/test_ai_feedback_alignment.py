"""Unit and integration tests for BCS AI Feedback Alignment and Evaluation (Requirement 6).

Covers:
1. Exact file matching (File A vs File B on same case).
2. File version / hash change mismatch.
3. Stale AI review run handling (no fake comparison).
4. No AI review run handling (no AI result).
5. BCS decision modification and full audit history.
6. Non-final decisions (HOLD / REQUEST_SUPPLEMENT) not treated as ground truth or finalized.
7. RBAC permissions (only ADMIN can view/verify).
8. Evaluation metrics strictly computed over verified ground truth cases only.
"""

from datetime import datetime, timezone
import pytest
from api.app.models.entities import (
    AiAgentStep,
    AiReviewRun,
    AuditEvent,
    BcsAiFeedback,
    Case,
    Claim,
    EvidenceFile,
)
from api.app.services.ai_review_service import build_case_snapshot
from api.tests.conftest import login_helper


def _create_evidence(db, claim, original_name="cert.pdf", sha256="hash111", version_no=1, uploader_id="sv001"):
    file_record = EvidenceFile(
        claim_id=claim.id,
        storage_key=f"storage/{sha256}.pdf",
        original_name=original_name,
        mime_type="application/pdf",
        size_bytes=1024,
        sha256=sha256,
        uploaded_by=uploader_id,
        version_no=version_no,
        is_current=True,
    )
    db.add(file_record)
    db.commit()
    db.refresh(file_record)
    return file_record


def _create_completed_ai_run(db, case, evidence_items, assessments=None, status="NEEDS_HUMAN", model="gemini-3.5-flash-lite + gemini-3.6-flash"):
    """Creates a mock AiReviewRun matching the real processing flow with AI_TRANSPARENCY step assessments."""
    rubric_version, evidence_fingerprint, snapshot = build_case_snapshot(db, case)
    run = AiReviewRun(
        case_id=case.id,
        requested_by=case.student_id,
        case_version=case.version,
        rubric_version=rubric_version,
        evidence_fingerprint=evidence_fingerprint,
        idempotency_key=f"idemp_{case.id}_{case.version}_{datetime.utcnow().timestamp()}",
        snapshot_json=snapshot,
        status=status,
        model=model,
        prompt_version="v1.0 + v1.0",
        created_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.flush()

    assessments_data = assessments or []
    step_read = AiAgentStep(
        run_id=run.id,
        kind="AI_READ",
        sort_order=1,
        status="COMPLETED",
        output_json={"files": [{"evidence_file_id": ev.id, "sha256": ev.sha256, "readable": True} for ev in evidence_items]},
    )
    step_transparency = AiAgentStep(
        run_id=run.id,
        kind="AI_TRANSPARENCY",
        sort_order=2,
        status="COMPLETED",
        output_json={"assessments": assessments_data},
    )
    db.add(step_read)
    db.add(step_transparency)
    db.commit()
    db.refresh(run)
    return run


def test_link_matching_exact_file_only(client, seed_data, db):
    """1. ĐÚNG/SAI TỆP: Decision on File A links to File A's AI run; File B on same case does not link to File A's result."""
    case = seed_data["cases"][0]
    case.status = "BCS_REVIEW"
    claims = db.query(Claim).filter(Claim.case_id == case.id).all()
    claim1 = claims[0]
    claim2 = claims[1]

    file_a = _create_evidence(db, claim1, original_name="file_a.pdf", sha256="sha_aaa_111")
    file_b = _create_evidence(db, claim2, original_name="file_b.pdf", sha256="sha_bbb_222")

    # AI run only assessed File A with FLAGGED
    _create_completed_ai_run(
        db,
        case,
        evidence_items=[file_a, file_b],
        assessments=[
            {
                "evidence_file_id": file_a.id,
                "sha256": file_a.sha256,
                "criterion_code": "TC01",
                "verdict": "FLAGGED",
                "reason": "Phát hiện ngày cấp mâu thuẫn trên chứng chỉ A",
            }
        ],
    )

    bcs = login_helper(client, "bcs001")

    # Decision on File A: BCS accepts it despite AI flag
    resp_a = client.put(
        f"/api/v1/bcs/cases/{case.id}/evidence/{file_a.id}/decision",
        cookies=bcs["cookies"],
        headers=bcs["headers"],
        json={"decision": "ACCEPT", "reason": "BCS đã kiểm tra qua danh sách khoa", "expected_version": case.version},
    )
    assert resp_a.status_code == 200

    fb_a = db.query(BcsAiFeedback).filter(BcsAiFeedback.evidence_file_id == file_a.id).first()
    assert fb_a is not None
    assert fb_a.matching_status == "MATCHED"
    assert fb_a.ai_verdict == "FLAGGED"
    assert fb_a.bcs_decision == "ACCEPT"
    assert fb_a.discrepancy_status == "NEEDS_REVIEW"

    # Reload case version
    db.refresh(case)

    # Decision on File B: BCS accepts it, but AI did NOT assess File B
    resp_b = client.put(
        f"/api/v1/bcs/cases/{case.id}/evidence/{file_b.id}/decision",
        cookies=bcs["cookies"],
        headers=bcs["headers"],
        json={"decision": "ACCEPT", "reason": "Minh chứng B rõ ràng", "expected_version": case.version},
    )
    assert resp_b.status_code == 200

    fb_b = db.query(BcsAiFeedback).filter(BcsAiFeedback.evidence_file_id == file_b.id).first()
    assert fb_b is not None
    assert fb_b.matching_status == "NO_MATCHING_ASSESSMENT"
    assert fb_b.discrepancy_status == "NO_AI_RESULT"
    assert fb_b.ai_verdict is None


def test_evidence_file_version_hash_mismatch(client, seed_data, db):
    """2. TỆP THAY PHIÊN BẢN: Evidence file hash changed since AI run -> detects mismatch, no fake comparison."""
    case = seed_data["cases"][0]
    case.status = "BCS_REVIEW"
    claim = db.query(Claim).filter(Claim.case_id == case.id).first()

    old_file = _create_evidence(db, claim, original_name="cert_v1.pdf", sha256="old_sha_123", version_no=1)

    # AI run ran on old_sha_123
    _create_completed_ai_run(
        db,
        case,
        evidence_items=[old_file],
        assessments=[
            {
                "evidence_file_id": old_file.id,
                "sha256": "old_sha_123",
                "verdict": "SUPPORTED",
                "reason": "Hợp lệ",
            }
        ],
    )

    # Now student re-uploaded or file was updated to v2 with a new hash
    old_file.sha256 = "new_sha_999"
    old_file.version_no = 2
    db.commit()

    bcs = login_helper(client, "bcs001")
    resp = client.put(
        f"/api/v1/bcs/cases/{case.id}/evidence/{old_file.id}/decision",
        cookies=bcs["cookies"],
        headers=bcs["headers"],
        json={"decision": "ACCEPT", "reason": "Minh chứng mới", "expected_version": case.version},
    )
    assert resp.status_code == 200

    fb = db.query(BcsAiFeedback).filter(BcsAiFeedback.evidence_file_id == old_file.id).first()
    assert fb.matching_status == "STALE_AI_RUN"
    assert fb.discrepancy_status == "NO_AI_RESULT"
    assert fb.ai_verdict is None


def test_stale_ai_run_handling(client, seed_data, db):
    """3. AI RUN CŨ / STALE: AI review run is stale -> recorded as stale / no AI result, no fake comparison."""
    case = seed_data["cases"][0]
    case.status = "BCS_REVIEW"
    claim = db.query(Claim).filter(Claim.case_id == case.id).first()
    file_record = _create_evidence(db, claim, original_name="cert.pdf", sha256="sha_stale_111")

    run = _create_completed_ai_run(
        db,
        case,
        evidence_items=[file_record],
        assessments=[
            {
                "evidence_file_id": file_record.id,
                "sha256": file_record.sha256,
                "verdict": "SUPPORTED",
                "reason": "Hợp lệ",
            }
        ],
    )

    # Mark the AI run as stale
    run.status = "STALE"
    db.commit()

    bcs = login_helper(client, "bcs001")
    resp = client.put(
        f"/api/v1/bcs/cases/{case.id}/evidence/{file_record.id}/decision",
        cookies=bcs["cookies"],
        headers=bcs["headers"],
        json={"decision": "REJECT_ITEM", "reason": "Từ chối", "expected_version": case.version},
    )
    assert resp.status_code == 200

    fb = db.query(BcsAiFeedback).filter(BcsAiFeedback.evidence_file_id == file_record.id).first()
    assert fb.matching_status == "STALE_AI_RUN"
    assert fb.discrepancy_status == "NO_AI_RESULT"


def test_no_ai_run_handling(client, seed_data, db):
    """4. KHÔNG CÓ AI RUN: Case has no AI run -> recorded as NO_AI_RUN / NO_AI_RESULT."""
    case = seed_data["cases"][0]
    case.status = "BCS_REVIEW"
    claim = db.query(Claim).filter(Claim.case_id == case.id).first()
    file_record = _create_evidence(db, claim, original_name="cert_no_ai.pdf", sha256="sha_no_ai")

    bcs = login_helper(client, "bcs001")
    resp = client.put(
        f"/api/v1/bcs/cases/{case.id}/evidence/{file_record.id}/decision",
        cookies=bcs["cookies"],
        headers=bcs["headers"],
        json={"decision": "ACCEPT", "reason": "BCS duyệt hồ sơ không qua AI", "expected_version": case.version},
    )
    assert resp.status_code == 200

    fb = db.query(BcsAiFeedback).filter(BcsAiFeedback.evidence_file_id == file_record.id).first()
    assert fb.matching_status == "NO_AI_RUN"
    assert fb.discrepancy_status == "NO_AI_RESULT"
    assert fb.ai_run_id is None
    assert fb.ai_verdict is None


def test_bcs_decision_update_and_audit_history(client, seed_data, db):
    """5. BCS SỬA QUYẾT ĐỊNH: Feedback record updates and preserves previous state in audit_events."""
    case = seed_data["cases"][0]
    case.status = "BCS_REVIEW"
    claim = db.query(Claim).filter(Claim.case_id == case.id).first()
    file_record = _create_evidence(db, claim, original_name="cert.pdf", sha256="sha_audit_test")

    _create_completed_ai_run(
        db,
        case,
        evidence_items=[file_record],
        assessments=[
            {
                "evidence_file_id": file_record.id,
                "sha256": file_record.sha256,
                "verdict": "FLAGGED",
                "reason": "Nghi ngờ làm mờ ngày cấp",
            }
        ],
    )

    bcs = login_helper(client, "bcs001")

    # 1st decision: HOLD
    resp1 = client.put(
        f"/api/v1/bcs/cases/{case.id}/evidence/{file_record.id}/decision",
        cookies=bcs["cookies"],
        headers=bcs["headers"],
        json={"decision": "HOLD", "reason": "Cần kiểm tra lại", "expected_version": case.version},
    )
    assert resp1.status_code == 200

    fb = db.query(BcsAiFeedback).filter(BcsAiFeedback.evidence_file_id == file_record.id).first()
    assert fb.bcs_decision == "HOLD"
    assert fb.discrepancy_status == "NON_FINAL_DECISION"

    db.refresh(case)

    # 2nd decision: BCS changes to ACCEPT after manual check
    resp2 = client.put(
        f"/api/v1/bcs/cases/{case.id}/evidence/{file_record.id}/decision",
        cookies=bcs["cookies"],
        headers=bcs["headers"],
        json={"decision": "ACCEPT", "reason": "Đã đối chiếu danh sách giấy của Liên Chi đoàn", "expected_version": case.version},
    )
    assert resp2.status_code == 200

    db.refresh(fb)
    assert fb.bcs_decision == "ACCEPT"
    assert fb.discrepancy_status == "NEEDS_REVIEW"

    # Verify audit_events
    events = (
        db.query(AuditEvent)
        .filter(AuditEvent.case_id == case.id, AuditEvent.action.in_(["BCS_AI_FEEDBACK_RECORDED", "BCS_AI_FEEDBACK_UPDATED"]))
        .order_by(AuditEvent.created_at.asc())
        .all()
    )
    assert len(events) >= 2
    recorded_event = events[0]
    updated_event = events[1]
    assert recorded_event.action == "BCS_AI_FEEDBACK_RECORDED"
    assert updated_event.action == "BCS_AI_FEEDBACK_UPDATED"
    assert updated_event.before_json["bcs_decision"] == "HOLD"
    assert updated_event.after_json["bcs_decision"] == "ACCEPT"


def test_non_final_decisions_not_ground_truth(client, seed_data, db):
    """6. HOLD / REQUEST_SUPPLEMENT: Classified as NON_FINAL_DECISION, never treated as ground truth or AI right/wrong."""
    case = seed_data["cases"][0]
    case.status = "BCS_REVIEW"
    claim = db.query(Claim).filter(Claim.case_id == case.id).first()
    file_record = _create_evidence(db, claim, original_name="cert.pdf", sha256="sha_hold_test")

    _create_completed_ai_run(
        db,
        case,
        evidence_items=[file_record],
        assessments=[
            {
                "evidence_file_id": file_record.id,
                "sha256": file_record.sha256,
                "verdict": "SUPPORTED",
                "reason": "Hợp lệ",
            }
        ],
    )

    bcs = login_helper(client, "bcs001")
    resp = client.put(
        f"/api/v1/bcs/cases/{case.id}/evidence/{file_record.id}/decision",
        cookies=bcs["cookies"],
        headers=bcs["headers"],
        json={"decision": "HOLD", "reason": "Tạm dừng xem xét", "expected_version": case.version},
    )
    assert resp.status_code == 200

    fb = db.query(BcsAiFeedback).filter(BcsAiFeedback.evidence_file_id == file_record.id).first()
    assert fb.bcs_decision == "HOLD"
    assert fb.discrepancy_status == "NON_FINAL_DECISION"
    assert fb.ground_truth_status == "UNVERIFIED"
    assert fb.ground_truth_label is None


def test_rbac_admin_verification_and_unauthorized_blocking(client, seed_data, db):
    """7. PHÂN QUYỀN: Only ADMIN can access /admin/ai-feedback and verify ground truth; STUDENT/BCS get 403."""
    case = seed_data["cases"][0]
    case.status = "BCS_REVIEW"
    claim = db.query(Claim).filter(Claim.case_id == case.id).first()
    file_record = _create_evidence(db, claim, original_name="cert.pdf", sha256="sha_rbac_test")

    bcs = login_helper(client, "bcs001")
    client.put(
        f"/api/v1/bcs/cases/{case.id}/evidence/{file_record.id}/decision",
        cookies=bcs["cookies"],
        headers=bcs["headers"],
        json={"decision": "ACCEPT", "reason": "Duyệt", "expected_version": case.version},
    )

    fb = db.query(BcsAiFeedback).filter(BcsAiFeedback.evidence_file_id == file_record.id).first()
    assert fb is not None

    student = login_helper(client, "sv001")
    # Student blocked from list and verify
    assert client.get("/api/v1/admin/ai-feedback", cookies=student["cookies"]).status_code == 403
    assert client.post(f"/api/v1/admin/ai-feedback/{fb.id}/verify", cookies=student["cookies"], headers=student["headers"], json={"ground_truth_label": "SUPPORTED", "reason": "Lý do"}).status_code == 403

    # BCS blocked from list and verify
    assert client.get("/api/v1/admin/ai-feedback", cookies=bcs["cookies"]).status_code == 403
    assert client.post(f"/api/v1/admin/ai-feedback/{fb.id}/verify", cookies=bcs["cookies"], headers=bcs["headers"], json={"ground_truth_label": "SUPPORTED", "reason": "Lý do"}).status_code == 403

    # ADMIN allowed
    admin = login_helper(client, "admin001")
    res_list = client.get("/api/v1/admin/ai-feedback", cookies=admin["cookies"])
    assert res_list.status_code == 200

    res_verify = client.post(
        f"/api/v1/admin/ai-feedback/{fb.id}/verify",
        cookies=admin["cookies"],
        headers=admin["headers"],
        json={"ground_truth_label": "SUPPORTED", "reason": "Admin đã xác minh với nhà trường"},
    )
    assert res_verify.status_code == 200
    verified_data = res_verify.json()
    assert verified_data["ground_truth_status"] == "VERIFIED"
    assert verified_data["ground_truth_label"] == "SUPPORTED"


def test_metrics_strictly_verified_only(client, seed_data, db):
    """8. CHỈ SỐ CHỈ TÍNH CA CÓ NHÃN XÁC NHẬN: Unverified cases are excluded from accuracy & confusion matrix."""
    case = seed_data["cases"][0]
    case.status = "BCS_REVIEW"
    claim = db.query(Claim).filter(Claim.case_id == case.id).first()

    f1 = _create_evidence(db, claim, original_name="f1.pdf", sha256="sha_f1")
    f2 = _create_evidence(db, claim, original_name="f2.pdf", sha256="sha_f2")
    f3 = _create_evidence(db, claim, original_name="f3.pdf", sha256="sha_f3")

    _create_completed_ai_run(
        db,
        case,
        evidence_items=[f1, f2, f3],
        assessments=[
            {"evidence_file_id": f1.id, "sha256": f1.sha256, "verdict": "FLAGGED", "reason": "Cờ 1"},
            {"evidence_file_id": f2.id, "sha256": f2.sha256, "verdict": "SUPPORTED", "reason": "Hợp lệ 2"},
            {"evidence_file_id": f3.id, "sha256": f3.sha256, "verdict": "FLAGGED", "reason": "Cờ 3"},
        ],
    )

    bcs = login_helper(client, "bcs001")
    client.put(f"/api/v1/bcs/cases/{case.id}/evidence/{f1.id}/decision", cookies=bcs["cookies"], headers=bcs["headers"], json={"decision": "ACCEPT", "reason": "Lý do 1", "expected_version": case.version})
    db.refresh(case)
    client.put(f"/api/v1/bcs/cases/{case.id}/evidence/{f2.id}/decision", cookies=bcs["cookies"], headers=bcs["headers"], json={"decision": "ACCEPT", "reason": "Lý do 2", "expected_version": case.version})
    db.refresh(case)
    client.put(f"/api/v1/bcs/cases/{case.id}/evidence/{f3.id}/decision", cookies=bcs["cookies"], headers=bcs["headers"], json={"decision": "ACCEPT", "reason": "Lý do 3", "expected_version": case.version})

    admin = login_helper(client, "admin001")

    # Before any verification: metrics must show 0 verified, accuracy is None
    res_m0 = client.get("/api/v1/admin/ai-feedback-metrics", cookies=admin["cookies"]).json()
    assert res_m0["verified_matched_count"] == 0
    assert res_m0["ai_accuracy"] is None

    # Now verify ONLY f3 with ground truth FLAGGED (AI was right!)
    fb3 = db.query(BcsAiFeedback).filter(BcsAiFeedback.evidence_file_id == f3.id).first()
    client.post(
        f"/api/v1/admin/ai-feedback/{fb3.id}/verify",
        cookies=admin["cookies"],
        headers=admin["headers"],
        json={"ground_truth_label": "FLAGGED", "reason": "Minh chứng giả mạo chữ ký"},
    )

    # Metrics after 1 verified case: strictly calculated only over f3
    res_m1 = client.get("/api/v1/admin/ai-feedback-metrics", cookies=admin["cookies"]).json()
    assert res_m1["verified_matched_count"] == 1
    assert res_m1["ai_accuracy"] == 1.0  # AI predicted FLAGGED, GT was FLAGGED
    assert res_m1["confusion_matrix"]["FLAGGED"]["FLAGGED"] == 1
    # f1 and f2 are still UNVERIFIED, so they are excluded!
    assert res_m1["unverified_count"] >= 2


def test_bcs_decision_change_resets_ground_truth_and_excludes_from_metrics(client, seed_data, db):
    """REVIEW FIX 1: Khi BCS đổi quyết định, nhãn xác nhận cũ bị xóa (reset về UNVERIFIED) và ca đó bị loại khỏi metrics."""
    case = seed_data["cases"][0]
    case.status = "BCS_REVIEW"
    claim = db.query(Claim).filter(Claim.case_id == case.id).first()
    file_record = _create_evidence(db, claim, original_name="cert_reset.pdf", sha256="sha_reset_gt")

    _create_completed_ai_run(
        db,
        case,
        evidence_items=[file_record],
        assessments=[
            {
                "evidence_file_id": file_record.id,
                "sha256": file_record.sha256,
                "verdict": "FLAGGED",
                "reason": "Phát hiện dấu hiệu làm mờ",
            }
        ],
    )

    bcs = login_helper(client, "bcs001")
    # 1. BCS duyệt ACCEPT
    resp1 = client.put(
        f"/api/v1/bcs/cases/{case.id}/evidence/{file_record.id}/decision",
        cookies=bcs["cookies"],
        headers=bcs["headers"],
        json={"decision": "ACCEPT", "reason": "BCS duyệt tạm thời", "expected_version": case.version},
    )
    assert resp1.status_code == 200

    fb = db.query(BcsAiFeedback).filter(BcsAiFeedback.evidence_file_id == file_record.id).first()
    assert fb.bcs_decision == "ACCEPT"
    assert fb.ground_truth_status == "UNVERIFIED"

    # 2. ADMIN xác nhận nhãn chuẩn FLAGGED
    admin = login_helper(client, "admin001")
    resp_v = client.post(
        f"/api/v1/admin/ai-feedback/{fb.id}/verify",
        cookies=admin["cookies"],
        headers=admin["headers"],
        json={"ground_truth_label": "FLAGGED", "reason": "Xác minh chính xác"},
    )
    assert resp_v.status_code == 200
    db.refresh(fb)
    assert fb.ground_truth_status == "VERIFIED"
    assert fb.ground_truth_label == "FLAGGED"

    # Metrics hiển thị 1 ca đã xác nhận
    m1 = client.get("/api/v1/admin/ai-feedback-metrics", cookies=admin["cookies"]).json()
    assert m1["verified_matched_count"] == 1
    assert m1["ai_accuracy"] == 1.0

    # 3. BCS thay đổi quyết định sang REJECT_ITEM
    db.refresh(case)
    resp2 = client.put(
        f"/api/v1/bcs/cases/{case.id}/evidence/{file_record.id}/decision",
        cookies=bcs["cookies"],
        headers=bcs["headers"],
        json={"decision": "REJECT_ITEM", "reason": "BCS kiểm tra lại và từ chối", "expected_version": case.version},
    )
    assert resp2.status_code == 200

    # Kiểm tra nhãn chuẩn bị xóa (reset về UNVERIFIED) và lưu old_bcs_decision
    db.refresh(fb)
    assert fb.bcs_decision == "REJECT_ITEM"
    assert fb.ground_truth_status == "UNVERIFIED"
    assert fb.ground_truth_label is None
    assert fb.verification_reason is None
    assert fb.verified_by is None
    assert fb.verified_at is None

    # Kiểm tra ca này đã bị LOẠI KHỎI METRICS
    m2 = client.get("/api/v1/admin/ai-feedback-metrics", cookies=admin["cookies"]).json()
    assert m2["verified_matched_count"] == 0
    assert m2["ai_accuracy"] is None

    # Kiểm tra audit_event ghi nhận old_bcs_decision
    updated_event = (
        db.query(AuditEvent)
        .filter(AuditEvent.case_id == case.id, AuditEvent.action == "BCS_AI_FEEDBACK_UPDATED")
        .order_by(AuditEvent.created_at.desc())
        .first()
    )
    assert updated_event is not None
    assert updated_event.before_json["bcs_decision"] == "ACCEPT"
    assert updated_event.after_json["old_bcs_decision"] == "ACCEPT"
    assert updated_event.after_json["bcs_decision"] == "REJECT_ITEM"


def test_no_transparency_assessment_not_inferred_from_ai_read_and_excluded_from_metrics(client, seed_data, db):
    """REVIEW FIX 2: Không suy ra verdict minh bạch từ AI_READ; nếu không có assessment trong AI_TRANSPARENCY, ghi NO_MATCHING_ASSESSMENT và loại khỏi metrics."""
    case = seed_data["cases"][0]
    case.status = "BCS_REVIEW"
    claim = db.query(Claim).filter(Claim.case_id == case.id).first()
    file_record = _create_evidence(db, claim, original_name="cert_read_only.pdf", sha256="sha_read_only")

    # Run có bước AI_READ (đánh dấu file unreadable) nhưng bước AI_TRANSPARENCY KHÔNG có assessment cho file này
    rubric_version, evidence_fingerprint, snapshot = build_case_snapshot(db, case)
    run = AiReviewRun(
        case_id=case.id,
        requested_by=case.student_id,
        case_version=case.version,
        rubric_version=rubric_version,
        evidence_fingerprint=evidence_fingerprint,
        idempotency_key=f"idemp_read_only_{datetime.utcnow().timestamp()}",
        snapshot_json=snapshot,
        status="COMPLETED",
        model="gemini-3.5-flash-lite",
        prompt_version="v1.0",
        created_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.flush()

    step_read = AiAgentStep(
        run_id=run.id,
        kind="AI_READ",
        sort_order=1,
        status="COMPLETED",
        output_json={
            "files": [
                {
                    "evidence_file_id": file_record.id,
                    "sha256": file_record.sha256,
                    "readable": False,
                    "unreadable_reason": "Ảnh bị mờ",
                }
            ]
        },
    )
    step_transparency = AiAgentStep(
        run_id=run.id,
        kind="AI_TRANSPARENCY",
        sort_order=2,
        status="COMPLETED",
        output_json={"assessments": []},  # Không có assessment cho file này!
    )
    db.add(step_read)
    db.add(step_transparency)
    db.commit()

    bcs = login_helper(client, "bcs001")
    resp = client.put(
        f"/api/v1/bcs/cases/{case.id}/evidence/{file_record.id}/decision",
        cookies=bcs["cookies"],
        headers=bcs["headers"],
        json={"decision": "ACCEPT", "reason": "BCS chấp nhận", "expected_version": case.version},
    )
    assert resp.status_code == 200

    fb = db.query(BcsAiFeedback).filter(BcsAiFeedback.evidence_file_id == file_record.id).first()
    assert fb is not None
    # Phải ghi nhận trạng thái thiếu kết quả, KHÔNG được suy ra FLAGGED từ AI_READ
    assert fb.matching_status == "NO_MATCHING_ASSESSMENT"
    assert fb.discrepancy_status == "NO_AI_RESULT"
    assert fb.ai_verdict is None

    # Ca này tự động bị loại khỏi metrics
    admin = login_helper(client, "admin001")
    m = client.get("/api/v1/admin/ai-feedback-metrics", cookies=admin["cookies"]).json()
    assert m["verified_matched_count"] == 0
    assert m["ai_accuracy"] is None


def test_admin_view_file_rbac_and_unauthorized_blocked(client, seed_data, db):
    """REVIEW FIX 3: ADMIN có quyền xem/tải tệp qua /api/v1/files/{id} và /api/v1/admin/files/{id}; người không có quyền bị chặn."""
    import io

    # Sinh viên sv001 nộp minh chứng
    auth_sv1 = login_helper(client, "sv001")
    case = seed_data["cases"][0]
    crit1 = seed_data["criteria"][0]

    pdf_bytes = io.BytesIO(b"%PDF-1.4 test admin access pdf content")
    resp_upload = client.post(
        f"/api/v1/student/cases/{case.id}/evidence",
        data={"criterion_id": crit1.id},
        files={"file": ("admin-test-cert.pdf", pdf_bytes, "application/pdf")},
        cookies=auth_sv1["cookies"],
        headers=auth_sv1["headers"],
    )
    assert resp_upload.status_code == 201
    file_id = resp_upload.json()["id"]

    admin = login_helper(client, "admin001")
    auth_sv2 = login_helper(client, "sv002")
    auth_gvcn = login_helper(client, "gvcn001")
    auth_bcs = login_helper(client, "bcs001")

    # 1. ADMIN được xem tệp qua /api/v1/files/{file_id}
    resp_admin_files = client.get(f"/api/v1/files/{file_id}", cookies=admin["cookies"])
    assert resp_admin_files.status_code == 200
    assert resp_admin_files.content == b"%PDF-1.4 test admin access pdf content"

    # 2. ADMIN được xem tệp qua endpoint quản trị /api/v1/admin/files/{file_id}
    resp_admin_route = client.get(f"/api/v1/admin/files/{file_id}", cookies=admin["cookies"])
    assert resp_admin_route.status_code == 200
    assert resp_admin_route.content == b"%PDF-1.4 test admin access pdf content"

    # 3. Người không có quyền bị chặn trên endpoint quản trị /api/v1/admin/files/{file_id}
    assert client.get(f"/api/v1/admin/files/{file_id}", cookies=auth_sv1["cookies"]).status_code == 403
    assert client.get(f"/api/v1/admin/files/{file_id}", cookies=auth_sv2["cookies"]).status_code == 403
    assert client.get(f"/api/v1/admin/files/{file_id}", cookies=auth_bcs["cookies"]).status_code == 403
    assert client.get(f"/api/v1/admin/files/{file_id}", cookies=auth_gvcn["cookies"]).status_code == 403

    # 4. Người không có quyền bị chặn trên /api/v1/files/{file_id}
    # Sinh viên khác sv002 bị 403
    assert client.get(f"/api/v1/files/{file_id}", cookies=auth_sv2["cookies"]).status_code == 403
    # GVCN bị 403
    assert client.get(f"/api/v1/files/{file_id}", cookies=auth_gvcn["cookies"]).status_code == 403

    # 5. Chưa đăng nhập (không có cookie) bị 401 trên cả hai endpoint
    client.cookies.clear()
    assert client.get(f"/api/v1/admin/files/{file_id}").status_code == 401
    assert client.get(f"/api/v1/files/{file_id}").status_code == 401


def test_system_fallback_assessment_model_none_excluded_from_quality_metrics(client, seed_data, db):
    """REVIEW: Phân biệt assessment do Gemini tạo với kết quả UNKNOWN dự phòng do hệ thống tạo (model=None);
    chấp nhận run NEEDS_HUMAN khi AI_TRANSPARENCY COMPLETED; chỉ kết quả thực sự từ mô hình mới được tính vào metrics."""
    case = seed_data["cases"][0]
    case.status = "BCS_REVIEW"
    claims = db.query(Claim).filter(Claim.case_id == case.id).all()
    claim1 = claims[0]
    claim2 = claims[1]

    # File 1: có kết quả dự phòng do hệ thống tạo (model=None, verdict=UNKNOWN)
    file_fallback = _create_evidence(db, claim1, original_name="cert_fallback.pdf", sha256="sha_fallback_123")
    # File 2: có kết quả thực sự từ mô hình Gemini (model="gemini-3.6-flash", verdict=SUPPORTED)
    file_gemini = _create_evidence(db, claim2, original_name="cert_gemini.pdf", sha256="sha_gemini_456")

    _create_completed_ai_run(
        db,
        case,
        evidence_items=[file_fallback, file_gemini],
        status="NEEDS_HUMAN",  # Trạng thái run giống luồng thật sau khi AI hoàn tất
        assessments=[
            {
                "evidence_file_id": file_fallback.id,
                "sha256": file_fallback.sha256,
                "criterion_code": "TC01",
                "verdict": "UNKNOWN",
                "reason": "Chưa đủ dữ kiện đọc được hoặc điều khoản để đối chiếu.",
                "model": None,  # Dự phòng hệ thống, KHÔNG gọi mô hình
                "prompt_version": "v1.0",
                "requires_human_review": True,
            },
            {
                "evidence_file_id": file_gemini.id,
                "sha256": file_gemini.sha256,
                "criterion_code": "TC02",
                "verdict": "SUPPORTED",
                "reason": "Minh chứng đầy đủ và hợp lệ",
                "model": "gemini-3.6-flash",  # Kết quả thực sự từ mô hình
                "prompt_version": "v1.0",
            },
        ],
    )

    bcs = login_helper(client, "bcs001")
    # BCS duyệt cả hai tệp: ACCEPT
    resp_fb = client.put(
        f"/api/v1/bcs/cases/{case.id}/evidence/{file_fallback.id}/decision",
        cookies=bcs["cookies"],
        headers=bcs["headers"],
        json={"decision": "ACCEPT", "reason": "BCS duyệt thủ công", "expected_version": case.version},
    )
    assert resp_fb.status_code == 200

    db.refresh(case)
    resp_gm = client.put(
        f"/api/v1/bcs/cases/{case.id}/evidence/{file_gemini.id}/decision",
        cookies=bcs["cookies"],
        headers=bcs["headers"],
        json={"decision": "ACCEPT", "reason": "BCS đồng thuận với AI", "expected_version": case.version},
    )
    assert resp_gm.status_code == 200

    # Kiểm tra bản ghi phản hồi File Fallback
    fb_record = db.query(BcsAiFeedback).filter(BcsAiFeedback.evidence_file_id == file_fallback.id).first()
    assert fb_record is not None
    assert fb_record.matching_status == "MATCHED"  # Khớp với run NEEDS_HUMAN thành công
    assert fb_record.ai_verdict == "UNKNOWN"
    assert fb_record.ai_model is None  # Đã phân biệt model=None

    # Kiểm tra bản ghi phản hồi File Gemini
    gm_record = db.query(BcsAiFeedback).filter(BcsAiFeedback.evidence_file_id == file_gemini.id).first()
    assert gm_record is not None
    assert gm_record.matching_status == "MATCHED"
    assert gm_record.ai_verdict == "SUPPORTED"
    assert gm_record.ai_model == "gemini-3.6-flash"

    admin = login_helper(client, "admin001")

    # Xác nhận nhãn chuẩn cho CẢ HAI ca
    client.post(
        f"/api/v1/admin/ai-feedback/{fb_record.id}/verify",
        cookies=admin["cookies"],
        headers=admin["headers"],
        json={"ground_truth_label": "SUPPORTED", "reason": "Xác nhận nhãn ca dự phòng"},
    )
    client.post(
        f"/api/v1/admin/ai-feedback/{gm_record.id}/verify",
        cookies=admin["cookies"],
        headers=admin["headers"],
        json={"ground_truth_label": "SUPPORTED", "reason": "Xác nhận nhãn ca Gemini"},
    )

    # Kiểm tra metrics: CHỈ có ca Gemini (model != None) được tính vào metrics đánh giá chất lượng AI!
    # Ca dự phòng hệ thống (model = None) bị loại khỏi accuracy và ma trận nhầm lẫn!
    metrics = client.get("/api/v1/admin/ai-feedback-metrics", cookies=admin["cookies"]).json()
    assert metrics["verified_count"] == 2
    assert metrics["verified_matched_count"] == 1  # Chỉ có 1 ca thực sự từ mô hình!
    assert metrics["ai_accuracy"] == 1.0  # Gemini đoán SUPPORTED, GT là SUPPORTED
    assert metrics["confusion_matrix"]["SUPPORTED"]["SUPPORTED"] == 1
    assert metrics["confusion_matrix"]["UNKNOWN"]["SUPPORTED"] == 0  # Fallback không bị đưa vào ma trận
