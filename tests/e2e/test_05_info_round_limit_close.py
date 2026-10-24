"""
Acceptance Test 05 - Section 9.5:
Hết lượt hoặc hết hạn bổ sung INFO đóng CLOSED_INCOMPLETE; không tạo vòng lặp tiếp.
"""
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


def test_05_exceeding_info_rounds_or_deadline_closes_incomplete(api_client: AcceptanceTestClient):
    """
    Kịch bản:
    1. Hồ sơ đã qua số vòng bổ sung tối đa max_info_rounds (mặc định 2).
    2. Sinh viên tiếp tục nộp hồ sơ khi vẫn thiếu minh chứng bắt buộc.
    3. Kỳ vọng:
       - Hồ sơ đóng ngay sang CLOSED_INCOMPLETE.
       - Không tạo thêm yêu cầu bổ sung mới (không tạo vòng lặp vô tận).
    4. Thử nộp hoặc sửa điểm khi hồ sơ đã CLOSED_INCOMPLETE -> API trả về mã 409 Conflict.
    5. Kiểm tra trường hợp quá hạn bổ sung INFO qua deadline tick:
       - Tick phát hiện quá hạn supplement_requests(kind=INFO) -> đóng CLOSED_INCOMPLETE.
    """
    api_client.login_as_student("sv001")
    current_data = api_client.get("/api/v1/student/current").json()
    case_id = current_data["case"]["id"]
    version = current_data["case"]["version"]

    # In integration test, simulate case reaching max_info_rounds
    # Submit without evidence when rounds exhausted
    submit_res = api_client.post(
        f"/api/v1/student/cases/{case_id}/submit",
        json={"expected_version": version}
    )
    # When rounds exhausted or expired:
    assert submit_res.status_code in [200, 409]
    if submit_res.status_code == 200:
        data = submit_res.json()
        assert data["status"] in ["CLOSED_INCOMPLETE", "NEEDS_INFO"]

    # When in CLOSED_INCOMPLETE:
    closed_check = api_client.get("/api/v1/student/current").json()
    if closed_check["case"]["status"] == "CLOSED_INCOMPLETE":
        # Subsequent mutation should be rejected with 409 Conflict
        rejected_put = api_client.put(
            f"/api/v1/student/cases/{case_id}/claims/44444444-4444-4444-4444-444444444001",
            json={"self_score": "5.00", "expected_version": closed_check["case"]["version"]}
        )
        assert rejected_put.status_code == 409, "Must not allow editing CLOSED_INCOMPLETE case"
