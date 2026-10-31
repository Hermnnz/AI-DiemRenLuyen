"""
Acceptance Test 07 - Section 9.7:
BCS nhập điểm vượt max hoặc khác tự khai mà không có lý do bị 422; tổng dự kiến cộng đúng.
"""
import io
import os
from datetime import datetime, timezone
import pytest
from tests.fixtures.client import AcceptanceTestClient

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.skipif(
        not os.getenv("RUN_ACCEPTANCE_TESTS"),
        reason="Chờ ghép backend/UI ở Giai đoạn 2 (Backend routes hiện là shell từ foundation-v1)"
    )
]


def test_07_bcs_scoring_validation_and_proposed_total(api_client: AcceptanceTestClient, monkeypatch):
    """
    Kịch bản:
    1. Sinh viên sv001 tự chấm điểm và nộp hồ sơ hợp lệ sang BCS_REVIEW.
    2. BCS nhập điểm duyệt approved_score vượt quá max_score (ví dụ 15.00 > 10.00) -> nhận 422.
    3. BCS nhập điểm duyệt khác điểm tự khai nhưng không kèm lý do (hoặc lý do rỗng) -> nhận 422.
    4. BCS nhập điểm duyệt hợp lệ kèm lý do giải trình khi khác tự khai -> nhận 200.
    5. Hoàn tất khi chưa quyết định minh chứng bị 422; BCS quyết định từng tệp.
    6. BCS hoàn tất đánh giá (complete-review) cho toàn bộ tiêu chí.
    7. Kỳ vọng:
       - Hồ sơ chuyển sang PROPOSED.
       - proposed_total được cộng chính xác từ các approved_score.
    """
    # Keep submission inside the fixture campaign window regardless of run date.
    from api.app.routes import student

    class SubmissionDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            fixed = cls(2026, 10, 26, 12, tzinfo=timezone.utc)
            return fixed.astimezone(tz) if tz else fixed.replace(tzinfo=None)

    monkeypatch.setattr(student, "datetime", SubmissionDateTime)

    # 1. Sinh viên sv001 nộp hồ sơ hoàn chỉnh sang BCS_REVIEW
    api_client.login_as_student("sv001")
    sv_data = api_client.get("/api/v1/student/current").json()
    case_id = sv_data["case"]["id"]
    version = sv_data["case"]["version"]
    criteria = sv_data["criteria"]

    for crit in criteria:
        put_res = api_client.put(
            f"/api/v1/student/cases/{case_id}/claims/{crit['id']}",
            json={"self_score": "8.00", "student_note": "Tự chấm mẫu", "expected_version": version}
        )
        assert put_res.status_code == 200
        version = put_res.json().get("version", version + 1)

        if crit.get("requires_evidence"):
            pdf = io.BytesIO(b"%PDF-1.4 evidence")
            up_res = api_client.post(
                f"/api/v1/student/cases/{case_id}/evidence",
                data={"criterion_id": crit["id"]},
                files={"file": (f"{crit['code']}.pdf", pdf, "application/pdf")}
            )
            assert up_res.status_code in [200, 201]

    sub_res = api_client.post(
        f"/api/v1/student/cases/{case_id}/submit",
        json={"expected_version": version}
    )
    assert sub_res.status_code == 200
    assert sub_res.json()["status"] == "BCS_REVIEW"
    case_version = sub_res.json()["version"]

    # 2. BCS đăng nhập và lấy thông tin hồ sơ
    api_client.logout()
    api_client.login_as_bcs("bcs001")
    crit1 = criteria[0]

    # 2. Score exceeds max_score (max is 10.00, input 15.00) -> 422
    res_exceed = api_client.put(
        f"/api/v1/bcs/cases/{case_id}/claims/{crit1['id']}/review",
        json={"approved_score": "15.00", "reason": "Chấm cao hơn max", "expected_version": case_version}
    )
    assert res_exceed.status_code == 422, "approved_score > max_score must return 422"

    # 3. Score differs from self_score without reason -> 422
    res_no_reason = api_client.put(
        f"/api/v1/bcs/cases/{case_id}/claims/{crit1['id']}/review",
        json={"approved_score": "6.00", "reason": "", "expected_version": case_version}
    )
    assert res_no_reason.status_code == 422, "Different score without reason must return 422"

    # 4. Valid score with valid reason for crit1
    res_valid1 = api_client.put(
        f"/api/v1/bcs/cases/{case_id}/claims/{crit1['id']}/review",
        json={
            "approved_score": "7.00",
            "reason": "Minh chứng chỉ đạt mức khá theo thang điểm quy chế",
            "expected_version": case_version
        }
    )
    assert res_valid1.status_code == 200
    current_version = res_valid1.json().get("version", case_version + 1)

    # 5. Chấm tiếp các tiêu chí còn lại
    expected_sum = 7.00
    for crit in criteria[1:]:
        res_crit = api_client.put(
            f"/api/v1/bcs/cases/{case_id}/claims/{crit['id']}/review",
            json={"approved_score": "8.00", "reason": None, "expected_version": current_version}
        )
        assert res_crit.status_code == 200
        current_version = res_crit.json().get("version", current_version + 1)
        expected_sum += 8.00

    # 6. Missing per-file decisions must block completion without changing the case.
    detail_res = api_client.get(f"/api/v1/bcs/cases/{case_id}")
    assert detail_res.status_code == 200
    required_ids = detail_res.json()["evidence_review_required_ids"]
    assert required_ids, "Positive claims with uploaded evidence must require review"
    blocked = api_client.post(
        f"/api/v1/bcs/cases/{case_id}/complete-review",
        json={"expected_version": current_version}
    )
    assert blocked.status_code == 422
    assert blocked.json()["error"]["code"] == "EVIDENCE_DECISION_REQUIRED"
    unchanged = api_client.get(f"/api/v1/bcs/cases/{case_id}").json()
    assert unchanged["status"] == "BCS_REVIEW"
    assert unchanged["version"] == current_version

    for evidence_id in required_ids:
        decision = api_client.put(
            f"/api/v1/bcs/cases/{case_id}/evidence/{evidence_id}/decision",
            json={
                "decision": "ACCEPT",
                "reason": "Đã đối chiếu minh chứng với tiêu chí tương ứng",
                "expected_version": current_version,
            },
        )
        assert decision.status_code == 200, decision.text
        assert decision.json()["evidence_decision"]["decision"] == "ACCEPT"
        current_version = decision.json()["version"]

    # 7. Complete review only after every required evidence decision is recorded.
    complete_res = api_client.post(
        f"/api/v1/bcs/cases/{case_id}/complete-review",
        json={"expected_version": current_version}
    )
    assert complete_res.status_code == 200
    res_data = complete_res.json()
    assert res_data["status"] == "PROPOSED"
    assert float(res_data["proposed_total"]) == pytest.approx(expected_sum, abs=1e-2)
