"""
Acceptance Test 03 - Section 9.3:
Form lưu nháp rồi tải lại giữ nguyên điểm và tệp; tổng tự khai đúng.
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


def test_03_draft_persistence_and_claimed_total_calculation(api_client: AcceptanceTestClient):
    """
    Kịch bản:
    1. Sinh viên sv001 đăng nhập, lấy case hiện tại ở trạng thái DRAFT.
    2. Tải lên tệp minh chứng cho tiêu chí TC01.
    3. Cập nhật điểm tự khai TC01 = 8.50 và TC02 = 9.00 kèm ghi chú sinh viên.
    4. Tải lại trang (GET /api/v1/student/current).
    5. Kiểm tra: Điểm tự khai, ghi chú và tệp minh chứng giữ nguyên.
    6. Kiểm tra: claimed_total được tính chính xác bằng 17.50 (8.50 + 9.00).
    """
    api_client.login_as_student("sv001")
    current_data = api_client.get("/api/v1/student/current").json()
    case_id = current_data["case"]["id"]
    version = current_data["case"]["version"]

    criteria_map = {c["code"]: c["id"] for c in current_data["criteria"]}
    tc01_id = criteria_map["TC01"]
    tc02_id = criteria_map["TC02"]

    # 1. Upload evidence file for TC01
    pdf_content = b"%PDF-1.4 sample evidence content"
    files = {"file": ("minh_chung_nckh.pdf", io.BytesIO(pdf_content), "application/pdf")}
    upload_res = api_client.post(
        f"/api/v1/student/cases/{case_id}/evidence",
        data={"criterion_id": tc01_id},
        files=files
    )
    assert upload_res.status_code in [200, 201]
    evidence_meta = upload_res.json()
    assert evidence_meta["original_name"] == "minh_chung_nckh.pdf"

    # 2. Save claim TC01
    put_tc01 = api_client.put(
        f"/api/v1/student/cases/{case_id}/claims/{tc01_id}",
        json={"self_score": "8.50", "student_note": "Báo cáo NCKH cấp khoa", "expected_version": version}
    )
    assert put_tc01.status_code == 200
    version = put_tc01.json().get("version", version + 1)

    # 3. Save claim TC02
    put_tc02 = api_client.put(
        f"/api/v1/student/cases/{case_id}/claims/{tc02_id}",
        json={"self_score": "9.00", "student_note": "Hoạt động hiến máu nhân đạo", "expected_version": version}
    )
    assert put_tc02.status_code == 200

    # 4. Reload form via GET /api/v1/student/current
    reloaded = api_client.get("/api/v1/student/current").json()
    claims = {c["criterion_id"]: c for c in reloaded["claims"]}

    # 5. Assertions on persistence
    assert claims[tc01_id]["self_score"] == "8.50"
    assert claims[tc01_id]["student_note"] == "Báo cáo NCKH cấp khoa"
    assert len(claims[tc01_id]["evidence"]) >= 1
    assert claims[tc01_id]["evidence"][0]["original_name"] == "minh_chung_nckh.pdf"

    assert claims[tc02_id]["self_score"] == "9.00"
    assert claims[tc02_id]["student_note"] == "Hoạt động hiến máu nhân đạo"

    # 6. Assert claimed_total = 17.50
    assert float(reloaded["case"]["claimed_total"]) == pytest.approx(17.50, abs=1e-2)
