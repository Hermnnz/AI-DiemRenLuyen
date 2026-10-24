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
    1. Sinh viên sv002 điền điểm tự chấm cho toàn bộ tiêu chí nhưng không tải minh chứng bắt buộc.
    2. Nộp lần 1: Thiếu minh chứng -> hồ sơ chuyển NEEDS_INFO (round 1).
    3. Nộp lần 2: Vẫn thiếu minh chứng -> hồ sơ chuyển NEEDS_INFO (round 2 = max_info_rounds).
    4. Nộp lần 3: Vượt quá số vòng bổ sung tối đa max_info_rounds (2) -> hồ sơ đóng ngay sang CLOSED_INCOMPLETE.
    5. Kỳ vọng:
       - Không tạo thêm yêu cầu bổ sung mới.
       - Thử nộp hoặc sửa điểm khi hồ sơ đã CLOSED_INCOMPLETE -> API trả về mã 409 Conflict.
    """
    api_client.login_as_student("sv002")
    current_data = api_client.get("/api/v1/student/current").json()
    case_id = current_data["case"]["id"]
    version = current_data["case"]["version"]
    criteria = current_data["criteria"]

    # Điền điểm cho toàn bộ tiêu chí
    for crit in criteria:
        put_res = api_client.put(
            f"/api/v1/student/cases/{case_id}/claims/{crit['id']}",
            json={"self_score": "8.00", "student_note": "Tự chấm mẫu", "expected_version": version}
        )
        assert put_res.status_code == 200
        version = put_res.json().get("version", version + 1)

    # Nộp lần 1 (thiếu minh chứng) -> NEEDS_INFO (round 1)
    res1 = api_client.post(
        f"/api/v1/student/cases/{case_id}/submit",
        json={"expected_version": version}
    )
    assert res1.status_code == 200
    assert res1.json()["status"] == "NEEDS_INFO"
    v1 = res1.json()["version"]

    # Nộp lần 2 (vẫn thiếu minh chứng) -> NEEDS_INFO (round 2)
    res2 = api_client.post(
        f"/api/v1/student/cases/{case_id}/submit",
        json={"expected_version": v1}
    )
    assert res2.status_code == 200
    assert res2.json()["status"] == "NEEDS_INFO"
    v2 = res2.json()["version"]

    # Nộp lần 3 (vượt quá max_info_rounds) -> CLOSED_INCOMPLETE
    res3 = api_client.post(
        f"/api/v1/student/cases/{case_id}/submit",
        json={"expected_version": v2}
    )
    assert res3.status_code == 200
    assert res3.json()["status"] == "CLOSED_INCOMPLETE"
    v3 = res3.json()["version"]

    # Thử nộp tiếp hoặc sửa điểm khi đã CLOSED_INCOMPLETE -> 409 Conflict
    res_rejected = api_client.post(
        f"/api/v1/student/cases/{case_id}/submit",
        json={"expected_version": v3}
    )
    assert res_rejected.status_code == 409
    assert res_rejected.json()["error"]["code"] == "INVALID_STATE"

    # Sửa claim cũng bị chặn
    crit0_id = criteria[0]["id"]
    put_rejected = api_client.put(
        f"/api/v1/student/cases/{case_id}/claims/{crit0_id}",
        json={"self_score": "5.00", "expected_version": v3}
    )
    assert put_rejected.status_code == 409
