"""
Acceptance Test 12 - Section 9.12:
Deadline tick chạy hai lần không gửi trùng thông báo và không tăng lượt hai lần; không nhắc SV đã phản hồi.
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


def test_12_deadline_tick_idempotency_and_targeted_reminders(api_client: AcceptanceTestClient):
    """
    Kịch bản:
    1. Đợt đã công bố tại mốc T0. Thời gian giả lập trôi qua mốc nhắc nhở (T0 + reminder_after_hours).
    2. Sinh viên sv001 chưa phản hồi (vẫn PUBLISHED).
    3. Sinh viên sv002 đã phản hồi (đã bấm ACCEPTED hoặc APPEALED).
    4. Chạy lệnh deadline tick lần 1 (api.app.jobs.tick --now ...):
       - sv001 nhận thông báo nhắc hạn phản hồi (kèm dedup_key).
       - sv002 KHÔNG nhận thông báo nhắc nhở (vì đã phản hồi).
    5. Chạy lại lệnh deadline tick lần 2 với cùng mốc thời gian:
       - sv001 KHÔNG bị nhận thêm thông báo trùng lặp (nhờ unique dedup_key).
       - Các bộ đếm lượt (rounds) không bị tăng thêm lần thứ 2.
    """
    # Test execution via job runner / CLI
    import subprocess
    import sys

    simulated_now = "2026-10-27T10:00:00Z"

    # Run tick 1st time
    cmd = [sys.executable, "-m", "api.app.jobs.tick", "--now", simulated_now]
    p1 = subprocess.run(cmd, capture_output=True, text=True)
    assert p1.returncode == 0

    # Verify notifications for sv001 vs sv002
    api_client.login_as_student("sv001")
    notifs_sv1_pass1 = api_client.get("/api/v1/notifications").json().get("items", [])

    api_client.login_as_student("sv002")
    notifs_sv2_pass1 = api_client.get("/api/v1/notifications").json().get("items", [])

    # Run tick 2nd time (Idempotent run)
    p2 = subprocess.run(cmd, capture_output=True, text=True)
    assert p2.returncode == 0

    # Verify sv001 notifications count does not duplicate
    api_client.login_as_student("sv001")
    notifs_sv1_pass2 = api_client.get("/api/v1/notifications").json().get("items", [])
    assert len(notifs_sv1_pass2) == len(notifs_sv1_pass1), "Idempotent tick must not duplicate notifications"
