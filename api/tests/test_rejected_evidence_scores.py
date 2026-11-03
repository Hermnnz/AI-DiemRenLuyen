from datetime import datetime, timezone
from decimal import Decimal

import pytest

from api.app.models.entities import AuditEvent, BcsEvidenceDecision, Claim, EvidenceFile
from api.tests.conftest import login_helper


@pytest.fixture
def reviewed_case(seed_data, db):
    case = seed_data["cases"][0]
    case.status = "BCS_REVIEW"
    case.claimed_total = Decimal("18.00")
    claims = db.query(Claim).filter_by(case_id=case.id).order_by(Claim.criterion_id).all()
    for claim in claims:
        claim.self_score = Decimal("6.00")
        claim.approved_score = Decimal("6.00")
    db.commit()
    return case, claims


def add_file(db, claim, case, suffix, *, current=True):
    file = EvidenceFile(claim_id=claim.id, storage_key=f"reject-{suffix}.png",
                        original_name=f"reject-{suffix}.png", mime_type="image/png",
                        size_bytes=100, sha256=(suffix * 64)[:64], uploaded_by=case.student_id,
                        version_no=1, is_current=current)
    db.add(file)
    db.commit()
    return file


def decide(client, bcs, case, file, decision="REJECT_ITEM", reason="Không đúng người hoặc học kỳ", version=None):
    return client.put(f"/api/v1/bcs/cases/{case.id}/evidence/{file.id}/decision",
                      json={"decision": decision, "reason": reason,
                            "expected_version": case.version if version is None else version},
                      cookies=bcs["cookies"], headers=bcs["headers"])


@pytest.mark.parametrize("criterion_index", [0, 1, 2])
def test_reject_only_file_zeros_any_criterion_and_completion_needs_no_manual_adjustment(
    client, seed_data, db, reviewed_case, criterion_index,
):
    case, claims = reviewed_case
    target = claims[criterion_index]
    case.proposed_total = Decimal("18.00")
    db.commit()
    file = add_file(db, target, case, "a")
    bcs = login_helper(client, "bcs001")
    original_version = case.version
    response = decide(client, bcs, case, file)
    assert response.status_code == 200
    adjustment = response.json()["score_adjustment"]
    assert adjustment["criterion_id"] == target.criterion_id
    assert adjustment["approved_score"] == "0.00"
    assert "Không đúng người hoặc học kỳ" in adjustment["bcs_reason"]
    db.expire_all()
    assert target.approved_score == 0 and target.self_score == 6
    assert target.bcs_reason == adjustment["bcs_reason"]
    assert target.reviewed_by == seed_data["users"]["bcs001"].id
    assert target.reviewed_at is not None
    assert case.version == original_version + 1
    assert case.proposed_total == Decimal("12.00")
    assert all(claim.approved_score == 6 for claim in claims if claim.id != target.id)
    detail = client.get(f"/api/v1/bcs/cases/{case.id}", cookies=bcs["cookies"]).json()
    assert next(item for item in detail["claims"] if item["criterion"]["id"] == target.criterion_id)["approved_score"] == "0.00"
    # No score-save API call between rejecting the file and completing review.
    completed = client.post(f"/api/v1/bcs/cases/{case.id}/complete-review",
                            json={"expected_version": case.version}, cookies=bcs["cookies"], headers=bcs["headers"])
    assert completed.status_code == 200
    assert completed.json()["proposed_total"] == "12.00"
    assert completed.json()["status"] == "PROPOSED"
    assert db.query(AuditEvent).filter_by(case_id=case.id, action="BCS_SCORE_ZEROED_AFTER_EVIDENCE_REJECTION").count() == 1


@pytest.mark.parametrize("other_decision", [None, "ACCEPT", "HOLD"])
def test_mixed_or_pending_files_keep_score_until_every_current_file_is_rejected(
    client, db, reviewed_case, other_decision,
):
    case, claims = reviewed_case
    target = claims[0]
    first = add_file(db, target, case, "a")
    second = add_file(db, target, case, "b")
    bcs = login_helper(client, "bcs001")
    if other_decision:
        db.add(BcsEvidenceDecision(evidence_file_id=second.id, decision=other_decision,
                                  reason="Quyết định tệp thứ hai", reviewed_by=bcs["user"]["id"],
                                  reviewed_at=datetime.now(timezone.utc)))
        db.commit()
    response = decide(client, bcs, case, first, reason="Sai tên")
    assert response.status_code == 200 and response.json()["score_adjustment"] is None
    db.expire_all()
    assert target.approved_score == 6
    response = decide(client, bcs, case, second, reason="Sai học kỳ")
    assert response.status_code == 200
    assert response.json()["score_adjustment"]["approved_score"] == "0.00"
    db.expire_all()
    assert target.approved_score == 0
    assert "Sai tên" in target.bcs_reason and "Sai học kỳ" in target.bcs_reason


def test_non_current_accepted_file_does_not_prevent_zeroing(client, db, reviewed_case):
    case, claims = reviewed_case
    target = claims[0]
    old = add_file(db, target, case, "a", current=False)
    current = add_file(db, target, case, "b")
    bcs = login_helper(client, "bcs001")
    db.add(BcsEvidenceDecision(evidence_file_id=old.id, decision="ACCEPT", reason="Tệp cũ",
                              reviewed_by=bcs["user"]["id"], reviewed_at=datetime.now(timezone.utc)))
    db.commit()
    response = decide(client, bcs, case, current)
    assert response.status_code == 200 and response.json()["score_adjustment"]["approved_score"] == "0.00"


def test_stale_or_unauthorized_rejection_changes_neither_decision_nor_score(client, db, reviewed_case):
    case, claims = reviewed_case
    target = claims[0]
    file = add_file(db, target, case, "a")
    bcs = login_helper(client, "bcs001")
    assert decide(client, bcs, case, file, version=case.version - 1).status_code == 409
    other = login_helper(client, "bcs_other")
    assert decide(client, other, case, file).status_code == 403
    db.expire_all()
    assert target.approved_score == 6
    assert db.query(BcsEvidenceDecision).filter_by(evidence_file_id=file.id).count() == 0


def test_old_rejected_evidence_is_zeroed_on_completion_without_saving_points_again(client, db, reviewed_case):
    case, claims = reviewed_case
    target = claims[1]  # Optional-evidence criteria follow the same rejection rule.
    assert target.criterion.requires_evidence is False
    file = add_file(db, target, case, "a")
    bcs = login_helper(client, "bcs001")
    db.add(BcsEvidenceDecision(evidence_file_id=file.id, decision="REJECT_ITEM", reason="Đã từ chối trước bản vá",
                              reviewed_by=bcs["user"]["id"], reviewed_at=datetime.now(timezone.utc)))
    db.commit()
    response = client.post(f"/api/v1/bcs/cases/{case.id}/complete-review",
                           json={"expected_version": case.version}, cookies=bcs["cookies"], headers=bcs["headers"])
    assert response.status_code == 200 and response.json()["proposed_total"] == "12.00"
    db.expire_all()
    assert target.approved_score == 0
    assert "Đã từ chối trước bản vá" in target.bcs_reason


@pytest.mark.parametrize("save_mode", ["single", "batch"])
def test_saving_scores_cannot_restore_positive_points_while_all_evidence_is_rejected(
    client, db, reviewed_case, save_mode,
):
    case, claims = reviewed_case
    target = claims[0]
    file = add_file(db, target, case, "a")
    bcs = login_helper(client, "bcs001")
    assert decide(client, bcs, case, file).status_code == 200
    db.expire_all()
    if save_mode == "single":
        response = client.put(f"/api/v1/bcs/cases/{case.id}/claims/{target.criterion_id}/review",
                              json={"approved_score": "6.00", "expected_version": case.version},
                              cookies=bcs["cookies"], headers=bcs["headers"])
    else:
        response = client.post(f"/api/v1/bcs/cases/{case.id}/claims/review-batch",
                               json={"expected_version": case.version,
                                     "items": [{"criterion_id": claim.criterion_id, "approved_score": "6.00"}
                                               for claim in claims]},
                               cookies=bcs["cookies"], headers=bcs["headers"])
    assert response.status_code == 200
    db.expire_all()
    assert target.approved_score == 0
    assert all(claim.approved_score == 6 for claim in claims if claim.id != target.id)
