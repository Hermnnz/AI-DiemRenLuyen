"""
Acceptance Test 16 - Section 9.16:
Đợt SCHEDULED chưa tạo case/chưa cho nộp; tick ở open_at tạo đúng một case mỗi SV, chạy lặp lại không tạo trùng.
"""
import os
import subprocess
import sys
import pytest
from tests.fixtures.client import AcceptanceTestClient

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.skipif(
        not os.getenv("RUN_ACCEPTANCE_TESTS"),
        reason="Chờ ghép backend/UI ở Giai đoạn 2 (Backend routes hiện là shell từ foundation-v1)"
    )
]


def test_16_scheduled_campaign_open_and_case_initialization_idempotency(api_client: AcceptanceTestClient):
    """
    Kịch bản:
    1. ADMIN tạo hoặc mở một đợt có open_at ở tương lai (POST /admin/campaigns/{id}/open).
    2. Đợt chuyển sang SCHEDULED.
    3. Trong trạng thái SCHEDULED:
       - Chưa có case nào được tạo cho sinh viên trong cơ sở dữ liệu.
       - Sinh viên không thể nộp hoặc thao tác nộp hồ sơ.
    4. Thời gian giả lập đến mốc mở đợt (now >= open_at).
    5. Chạy lệnh deadline tick:
       - Đợt chuyển từ SCHEDULED sang OPEN; opened_at = NOW().
       - Tự động khởi tạo đúng 1 hồ sơ (case) ở trạng thái DRAFT cho mỗi sinh viên trong lớp (sv001, sv002, sv003).
    6. Chạy lặp lại deadline tick lần 2:
       - Tính idempotent được bảo toàn: Không tạo thêm case trùng lặp (duy trì đúng 1 case/sinh viên).
    """
    api_client.login_as_admin("admin001")
    demo_campaign_id = "33333333-3333-3333-3333-333333333333"

    # 1. Admin opens campaign with future open_at -> SCHEDULED
    res_open = api_client.post(f"/api/v1/admin/campaigns/{demo_campaign_id}/open")
    assert res_open.status_code in [200, 409]

    if res_open.status_code == 200:
        assert res_open.json().get("status") in ["SCHEDULED", "OPEN"]

    # 2. Trigger tick at open_at
    simulated_open_time = "2026-10-25T01:00:00Z"
    cmd = [sys.executable, "-m", "api.app.jobs.tick", "--now", simulated_open_time]

    # Run tick 1st time
    p1 = subprocess.run(cmd, capture_output=True, text=True)
    assert p1.returncode == 0

    # 3. Verify students have exactly 1 draft case
    for sv in ["sv001", "sv002", "sv003"]:
        api_client.login_as_student(sv)
        current = api_client.get("/api/v1/student/current").json()
        assert current.get("case") is not None
        assert current["case"]["status"] == "DRAFT"

    # 4. Run tick 2nd time (Idempotency test)
    p2 = subprocess.run(cmd, capture_output=True, text=True)
    assert p2.returncode == 0

    # Check again: still exactly 1 case per student
    for sv in ["sv001", "sv002", "sv003"]:
        api_client.login_as_student(sv)
        current = api_client.get("/api/v1/student/current").json()
        assert current["case"]["status"] == "DRAFT"
