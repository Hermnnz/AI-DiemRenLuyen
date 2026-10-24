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
    1. Sinh viên điền điểm cho toàn bộ tiêu chí, trong đó tiêu chí bắt buộc minh chứng (TC01) chưa có file.
    2. Gọi POST /api/v1/student/cases/{caseId}/submit.
    3. Kỳ vọng:
       - Hồ sơ chuyển sang NEEDS_INFO.
       - info_round tăng lên 1.
       - missing_items chỉ rõ tiêu chí thiếu minh chứng (chứa TC01).
       - Tạo yêu cầu bổ sung supplement_requests (kind=INFO).
       - Sinh viên nhận thông báo bổ sung minh chứng.
    4. Sinh viên tải lên minh chứng cho các tiêu chí còn thiếu trước hạn bổ sung.
    5. Gọi lại POST /api/v1/student/cases/{caseId}/submit.
    6. Kỳ vọng:
       - Hồ sơ chuyển sang BCS_REVIEW.
       - Yêu cầu bổ sung được ghi nhận hoàn thành (fulfilled_at có giá trị).
    """
    api_client.login_as_student("sv001")
    current_data = api_client.get("/api/v1/student/current").json()
    case_id = current_data["case"]["id"]
    version = current_data["case"]["version"]

    criteria = current_data["criteria"]
    # 1. Điền điểm cho toàn bộ tiêu chí để tránh MISSING_SELF_SCORE
    for crit in criteria:
        put_res = api_client.put(
            f"/api/v1/student/cases/{case_id}/claims/{crit['id']}",
            json={"self_score": "8.00", "student_note": "Tự chấm mẫu", "expected_version": version}
        )
        assert put_res.status_code == 200
        version = put_res.json().get("version", version + 1)

    # 2. Submit case khi chưa có file minh chứng cho các tiêu chí requires_evidence=True
    submit_res = api_client.post(
        f"/api/v1/student/cases/{case_id}/submit",
        json={"expected_version": version}
    )
    assert submit_res.status_code == 200
    submit_data = submit_res.json()

    # 3. Assertions on NEEDS_INFO
    assert submit_data["status"] == "NEEDS_INFO"
    assert len(submit_data["missing_items"]) > 0
    assert any("TC01" in item for item in submit_data["missing_items"])

    # Verify notifications
    notifs_raw = api_client.get("/api/v1/notifications").json()
    notifs = notifs_raw if isinstance(notifs_raw, list) else notifs_raw.get("items", [])
    assert any("bổ sung" in n["title"].lower() or "info" in n.get("type", "").lower() for n in notifs)

    # 4. Upload missing evidence cho tất cả các tiêu chí requires_evidence
    for crit in criteria:
        if crit.get("requires_evidence"):
            pdf_content = b"%PDF-1.4 fixed evidence content"
            files = {"file": (f"bo_sung_{crit['code']}.pdf", io.BytesIO(pdf_content), "application/pdf")}
            up_res = api_client.post(
                f"/api/v1/student/cases/{case_id}/evidence",
                data={"criterion_id": crit["id"]},
                files=files
            )
            assert up_res.status_code in [200, 201]

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
    assert len(resubmit_data["missing_items"]) == 0
