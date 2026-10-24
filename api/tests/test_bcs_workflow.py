import io
import pytest
from datetime import datetime, timezone, timedelta
from api.tests.conftest import login_helper
from api.app.models.entities import SupplementRequest
from api.app.services.deadline_service import run_deadline_tick


def _submit_complete_case(client, auth_sv, case, criteria):
    # Fulfill all criteria and evidence
    for crit in criteria:
        client.put(
            f"/api/v1/student/cases/{case.id}/claims/{crit.id}",
            json={"self_score": "8.00", "expected_version": case.version},
            cookies=auth_sv["cookies"],
            headers=auth_sv["headers"],
        )
        case.version += 1
        if crit.requires_evidence:
            pdf = io.BytesIO(b"%PDF evidence sample")
            client.post(
                f"/api/v1/student/cases/{case.id}/evidence",
                data={"criterion_id": crit.id},
                files={"file": (f"{crit.code}.pdf", pdf, "application/pdf")},
                cookies=auth_sv["cookies"],
                headers=auth_sv["headers"],
            )

    resp_sub = client.post(
        f"/api/v1/student/cases/{case.id}/submit",
        json={"expected_version": case.version},
        cookies=auth_sv["cookies"],
        headers=auth_sv["headers"],
    )
    assert resp_sub.status_code == 200
    assert resp_sub.json()["status"] == "BCS_REVIEW"
    case.version = resp_sub.json()["version"]
    case.status = "BCS_REVIEW"


def test_acceptance_criteria_6_bcs_request_proof_and_timeout(client, seed_data, db):
    """
    Tiêu chí 6: BCS yêu cầu PROOF, SV nộp lại; quá hạn PROOF quay BCS để kết luận, không tự trừ điểm.
    """
    auth_sv = login_helper(client, "sv001")
    auth_bcs = login_helper(client, "bcs001")
    case = seed_data["cases"][0]
    criteria = seed_data["criteria"]

    _submit_complete_case(client, auth_sv, case, criteria)

    # 1. BCS requests proof for TC01
    resp_req = client.post(
        f"/api/v1/bcs/cases/{case.id}/supplement-requests",
        json={
            "kind": "PROOF",
            "criterion_id": criteria[0].id,
            "reason": "Ảnh chứng chỉ bị mờ, vui lòng nộp lại bản rõ hơn",
            "expected_version": case.version,
        },
        cookies=auth_bcs["cookies"],
        headers=auth_bcs["headers"],
    )
    assert resp_req.status_code == 200
    supp_id = resp_req.json()["id"]

    # Case should now be in NEEDS_PROOF
    resp_detail = client.get(f"/api/v1/bcs/cases/{case.id}", cookies=auth_bcs["cookies"])
    assert resp_detail.json()["status"] == "NEEDS_PROOF"
    case.version = resp_detail.json()["version"]

    # 2. Simulate deadline expiration for this PROOF request
    # Set the deadline of supp_req to 1 hour ago
    supp_obj = db.query(SupplementRequest).filter(SupplementRequest.id == supp_id).first()
    past_time = datetime.now(timezone.utc) - timedelta(hours=1)
    supp_obj.deadline_at = past_time
    db.commit()

    # Run deadline tick at now
    stats = run_deadline_tick(db, datetime.now(timezone.utc))
    assert stats["returned_bcs_review_cases"] >= 1

    # Check case is returned to BCS_REVIEW with unchanged self_score (not docked)
    resp_detail2 = client.get(f"/api/v1/bcs/cases/{case.id}", cookies=auth_bcs["cookies"])
    assert resp_detail2.json()["status"] == "BCS_REVIEW"
    assert resp_detail2.json()["claims"][0]["self_score"] == "8.00"


def test_acceptance_criteria_7_bcs_review_score_validation_and_reasons(client, seed_data):
    """
    Tiêu chí 7: BCS nhập điểm vượt max hoặc khác tự khai mà không có lý do bị 422;
    tổng dự kiến cộng đúng.
    """
    auth_sv = login_helper(client, "sv001")
    auth_bcs = login_helper(client, "bcs001")
    case = seed_data["cases"][0]
    crit1, crit2, crit3 = seed_data["criteria"]

    _submit_complete_case(client, auth_sv, case, [crit1, crit2, crit3])

    # 1. Review with score > max_score (15.00 > 10.00) -> 422
    resp_over = client.put(
        f"/api/v1/bcs/cases/{case.id}/claims/{crit1.id}/review",
        json={"approved_score": "15.00", "reason": "Điểm vượt trần", "expected_version": case.version},
        cookies=auth_bcs["cookies"],
        headers=auth_bcs["headers"],
    )
    assert resp_over.status_code == 422
    assert resp_over.json()["error"]["code"] == "SCORE_OUT_OF_BOUNDS"

    # 2. Review with score != self_score (self is 8.00, approved is 6.00) but without reason -> 422
    resp_no_reason = client.put(
        f"/api/v1/bcs/cases/{case.id}/claims/{crit1.id}/review",
        json={"approved_score": "6.00", "reason": "", "expected_version": case.version},
        cookies=auth_bcs["cookies"],
        headers=auth_bcs["headers"],
    )
    assert resp_no_reason.status_code == 422
    assert resp_no_reason.json()["error"]["code"] == "REASON_REQUIRED"

    # 3. Review validly with score != self_score with reason
    resp_valid1 = client.put(
        f"/api/v1/bcs/cases/{case.id}/claims/{crit1.id}/review",
        json={"approved_score": "7.00", "reason": "Minh chứng chỉ đạt 70% yêu cầu", "expected_version": case.version},
        cookies=auth_bcs["cookies"],
        headers=auth_bcs["headers"],
    )
    assert resp_valid1.status_code == 200
    case.version = resp_valid1.json()["version"]

    # 4. Review TC02 (self=8.00, approved=8.00, reason optional)
    resp_valid2 = client.put(
        f"/api/v1/bcs/cases/{case.id}/claims/{crit2.id}/review",
        json={"approved_score": "8.00", "reason": None, "expected_version": case.version},
        cookies=auth_bcs["cookies"],
        headers=auth_bcs["headers"],
    )
    assert resp_valid2.status_code == 200
    case.version = resp_valid2.json()["version"]

    # 5. Review TC03 (self=8.00, approved=9.00 with reason)
    resp_valid3 = client.put(
        f"/api/v1/bcs/cases/{case.id}/claims/{crit3.id}/review",
        json={"approved_score": "9.00", "reason": "Tích cực hoạt động cộng đồng", "expected_version": case.version},
        cookies=auth_bcs["cookies"],
        headers=auth_bcs["headers"],
    )
    assert resp_valid3.status_code == 200
    case.version = resp_valid3.json()["version"]

    # 6. Complete review -> PROPOSED, sum = 7.00 + 8.00 + 9.00 = 24.00
    resp_comp = client.post(
        f"/api/v1/bcs/cases/{case.id}/complete-review",
        json={"expected_version": case.version},
        cookies=auth_bcs["cookies"],
        headers=auth_bcs["headers"],
    )
    assert resp_comp.status_code == 200
    assert resp_comp.json()["status"] == "PROPOSED"
    assert resp_comp.json()["proposed_total"] == "24.00"
