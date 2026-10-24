"""
Acceptance Test 04 - Section 9.4:
Nộp thiếu minh chứng bắt buộc tạo NEEDS_INFO và thông báo đúng mục; bổ sung đúng hạn quay lại BCS_REVIEW.
"""
import io
import os
import pytest
from tests.fixtures.client import AcceptanceTestClient

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.skipif(
        not os.getenv("RUN_ACCEPTANCE_TESTS"),
        reason="Chờ ghép backend/UI ở Giai đoạn 2 (Backend routes hiện là shell từ foundation-v1)"
    )
]


def test_04_missing_mandatory_evidence_triggers_needs_info_and_supplement_flow(api_client: AcceptanceTestClient):
    """
    Kịch bản:
    1. Sinh viên điền điểm cho tiêu chí TC01 (tiêu chí bắt buộc minh chứng requires_evidence=true) nhưng không đính kèm tệp.
    2. Gọi POST /api/v1/student/cases/{caseId}/submit.
    3. Kỳ vọng:
       - Hồ sơ chuyển sang NEEDS_INFO.
       - info_round tăng lên 1.
       - missing_items chỉ rõ tiêu chí TC01.
       - Tạo yêu cầu bổ sung supplement_requests (kind=INFO).
       - Sinh viên nhận thông báo bổ sung minh chứng.
    4. Sinh viên tải lên minh chứng cho TC01 trước hạn bổ sung.
    5. Gọi lại POST /api/v1/student/cases/{caseId}/submit.
    6. Kỳ vọng:
       - Hồ sơ chuyển sang BCS_REVIEW.
       - Yêu cầu bổ sung được ghi nhận hoàn thành (fulfilled_at có giá trị).
    """
    api_client.login_as_student("sv001")
    current_data = api_client.get("/api/v1/student/current").json()
    case_id = current_data["case"]["id"]
    version = current_data["case"]["version"]

    criteria_map = {c["code"]: c for c in current_data["criteria"]}
    tc01 = criteria_map["TC01"]
    assert tc01["requires_evidence"] is True

    # 1. Self score without evidence
    api_client.put(
        f"/api/v1/student/cases/{case_id}/claims/{tc01['id']}",
        json={"self_score": "10.00", "student_note": "Chưa có file", "expected_version": version}
    )

    # 2. Submit case
    submit_res = api_client.post(
        f"/api/v1/student/cases/{case_id}/submit",
        json={"expected_version": version + 1}
    )
    assert submit_res.status_code == 200
    submit_data = submit_res.json()

    # 3. Assertions on NEEDS_INFO
    assert submit_data["status"] == "NEEDS_INFO"
    assert len(submit_data["missing_items"]) > 0
    assert any(item["criterion_id"] == tc01["id"] for item in submit_data["missing_items"])

    # Verify notifications
    notifs = api_client.get("/api/v1/notifications").json()
    assert any("bổ sung" in n["title"].lower() or "info" in n.get("type", "").lower() for n in notifs.get("items", []))

    # 4. Upload missing evidence
    pdf_content = b"%PDF-1.4 fixed evidence content"
    files = {"file": ("bo_sung_tc01.pdf", io.BytesIO(pdf_content), "application/pdf")}
    api_client.post(
        f"/api/v1/student/cases/{case_id}/evidence",
        data={"criterion_id": tc01["id"]},
        files=files
    )

    # 5. Resubmit within deadline
    reloaded_version = api_client.get("/api/v1/student/current").json()["case"]["version"]
    resubmit_res = api_client.post(
        f"/api/v1/student/cases/{case_id}/submit",
        json={"expected_version": reloaded_version}
    )
    assert resubmit_res.status_code == 200
    resubmit_data = resubmit_res.json()

    # 6. Assert case returned to BCS_REVIEW
    assert resubmit_data["status"] == "BCS_REVIEW"
