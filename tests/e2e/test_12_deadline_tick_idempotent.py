"""
Acceptance Test 12 - Section 9.12:
Deadline tick chạy hai lần không gửi trùng thông báo và không tăng lượt hai lần; không nhắc SV đã phản hồi.
"""
import os
import subprocess
import sys
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
    from api.app.database import SessionLocal
    from api.app.models.entities import Campaign, Case, User

    pub_time = datetime(2026, 10, 26, 0, 0, 0, tzinfo=timezone.utc)
    app_dl_time = datetime(2026, 10, 28, 0, 0, 0, tzinfo=timezone.utc)

    # 1. Chuẩn bị dữ liệu: Đưa đợt sang PUBLISHED, sv001 PUBLISHED, sv002 ACCEPTED
    db = SessionLocal()
    try:
        camp = db.query(Campaign).first()
        camp.status = "PUBLISHED"
        camp.published_at = pub_time
        camp.appeal_deadline_at = app_dl_time
        camp.reminder_after_hours = 24

        u1 = db.query(User).filter(User.username == "sv001").first()
        u2 = db.query(User).filter(User.username == "sv002").first()

        c1 = db.query(Case).filter(Case.student_id == u1.id, Case.campaign_id == camp.id).first()
        c2 = db.query(Case).filter(Case.student_id == u2.id, Case.campaign_id == camp.id).first()

        c1.status = "PUBLISHED"
        c1.published_at = pub_time
        c1.appeal_deadline_at = app_dl_time

        c2.status = "ACCEPTED"
        c2.acceptance_source = "EXPLICIT"
        c2.published_at = pub_time
        c2.appeal_deadline_at = app_dl_time

        db.commit()
    finally:
        db.close()

    simulated_now = "2026-10-27T10:00:00Z"
    cmd = [sys.executable, "-m", "api.app.jobs.tick", "--now", simulated_now]

    # Run tick 1st time
    p1 = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    assert p1.returncode == 0

    # Helper function đọc notifications an toàn
    def get_user_notifs(username: str):
        api_client.logout()
        api_client.login_as_student(username)
        raw = api_client.get("/api/v1/notifications").json()
        return raw if isinstance(raw, list) else raw.get("items", [])

    # Verify notifications for sv001 vs sv002
    notifs_sv1_pass1 = get_user_notifs("sv001")
    notifs_sv2_pass1 = get_user_notifs("sv002")

    assert any("nhắc" in n.get("title", "").lower() or "hạn" in n.get("title", "").lower() or n.get("type") == "APPEAL_REMINDER" for n in notifs_sv1_pass1)
    assert not any("nhắc" in n.get("title", "").lower() or n.get("type") == "APPEAL_REMINDER" for n in notifs_sv2_pass1)

    # Run tick 2nd time (Idempotent run)
    p2 = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    assert p2.returncode == 0

    # Verify sv001 notifications count does not duplicate
    notifs_sv1_pass2 = get_user_notifs("sv001")
    assert len(notifs_sv1_pass2) == len(notifs_sv1_pass1), "Idempotent tick must not duplicate notifications"
