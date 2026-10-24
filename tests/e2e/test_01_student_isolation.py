"""
Acceptance Test 01 - Section 9.1:
STUDENT chỉ thấy case của chính mình; sửa ID trên URL/API để đọc case khác nhận 404/403.
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


def test_01_student_can_only_access_own_case(api_client: AcceptanceTestClient):
    """
    Kịch bản:
    1. Sinh viên sv001 đăng nhập thành công.
    2. Gọi GET /api/v1/student/current -> nhận case_id của chính mình (sv001).
    3. Thử sửa caseId trên URL để truy cập hoặc ghi đè case của sinh viên khác (sv002).
    4. Kỳ vọng: API trả về mã lỗi 403 Forbidden hoặc 404 Not Found theo chuẩn hợp đồng.
    5. Thử truy cập route của vai trò khác (/api/v1/bcs/... hoặc /api/v1/admin/...) -> nhận 403 Forbidden.
    """
    # 1. Login as sv001
    login_res = api_client.login_as_student("sv001")
    assert "csrf_token" in login_res

    # 2. Get current student case
    current_res = api_client.get("/api/v1/student/current")
    assert current_res.status_code == 200
    my_case = current_res.json().get("case", {})
    my_case_id = my_case.get("id")
    assert my_case_id is not None

    # Target victim case ID (sv002)
    other_case_id = "22222222-2222-2222-2222-222222222002"

    # 3. Attempt to access or mutate other student's case
    forbidden_get = api_client.get(f"/api/v1/student/cases/{other_case_id}")
    assert forbidden_get.status_code in [403, 404]
    data = forbidden_get.json()
    assert "error" in data
    assert data["error"]["code"] in ["FORBIDDEN", "NOT_FOUND", "UNAUTHORIZED"]

    # 4. Attempt to mutate other student's claim
    forbidden_put = api_client.put(
        f"/api/v1/student/cases/{other_case_id}/claims/44444444-4444-4444-4444-444444444001",
        json={"self_score": "10.00", "student_note": "Hacked", "expected_version": 1}
    )
    assert forbidden_put.status_code in [403, 404]

    # 5. Attempt to access BCS endpoints as student
    bcs_endpoint = api_client.get("/api/v1/bcs/campaigns/33333333-3333-3333-3333-333333333333/overview")
    assert bcs_endpoint.status_code == 403
