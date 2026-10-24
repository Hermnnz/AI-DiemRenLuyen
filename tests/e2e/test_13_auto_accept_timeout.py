"""
Acceptance Test 13 - Section 9.13:
Quá hạn phản hồi mà SV chưa đồng ý/khiếu nại thì thành ACCEPTED_AUTO đúng một lần; SV đã phản hồi không bị tự chấp nhận.
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


def test_13_appeal_deadline_timeout_auto_accept(api_client: AcceptanceTestClient):
    """
    Kịch bản:
    1. Đợt đã công bố với thời hạn phản hồi appeal_deadline_at.
    2. Ba sinh viên trong lớp có trạng thái phản hồi khác nhau:
       - sv001: Chưa phản hồi (hồ sơ vẫn PUBLISHED).
       - sv002: Đã gửi khiếu nại (hồ sơ đang APPEALED).
       - sv003: Đã chủ động bấm đồng ý (hồ sơ ACCEPTED, acceptance_source='EXPLICIT').
    3. Thời gian giả lập trôi qua quá hạn phản hồi (now > appeal_deadline_at).
    4. Chạy lệnh deadline tick:
       - Hồ sơ sv001 chuyển sang ACCEPTED_AUTO đúng một lần; acceptance_source = 'TIMEOUT'.
       - Hồ sơ sv002 GIỮ NGUYÊN trạng thái APPEALED (không bị tự động chấp thuận).
       - Hồ sơ sv003 GIỮ NGUYÊN acceptance_source = 'EXPLICIT'.
    5. Chạy lặp lại deadline tick: Không tạo chuyển trạng thái thừa hoặc thông báo trùng lặp.
    """
    from api.app.database import SessionLocal
    from api.app.models.entities import Campaign, Case, User

    pub_time = datetime(2026, 10, 26, 0, 0, 0, tzinfo=timezone.utc)
    app_dl_time = datetime(2026, 10, 30, 0, 0, 0, tzinfo=timezone.utc)

    # 1. Chuẩn bị dữ liệu ban đầu
    db = SessionLocal()
    try:
        camp = db.query(Campaign).first()
        camp.status = "PUBLISHED"
        camp.published_at = pub_time
        camp.appeal_deadline_at = app_dl_time

        u1 = db.query(User).filter(User.username == "sv001").first()
        u2 = db.query(User).filter(User.username == "sv002").first()
        u3 = db.query(User).filter(User.username == "sv003").first()

        c1 = db.query(Case).filter(Case.student_id == u1.id, Case.campaign_id == camp.id).first()
        c2 = db.query(Case).filter(Case.student_id == u2.id, Case.campaign_id == camp.id).first()
        c3 = db.query(Case).filter(Case.student_id == u3.id, Case.campaign_id == camp.id).first()

        c1.status = "PUBLISHED"
        c1.published_at = pub_time
        c1.appeal_deadline_at = app_dl_time
        c1.acceptance_source = None

        c2.status = "APPEALED"
        c2.published_at = pub_time
        c2.appeal_deadline_at = app_dl_time

        c3.status = "ACCEPTED"
        c3.published_at = pub_time
        c3.appeal_deadline_at = app_dl_time
        c3.acceptance_source = "EXPLICIT"

        db.commit()
    finally:
        db.close()

    post_deadline_time = "2026-10-31T00:00:00Z"
    cmd = [sys.executable, "-m", "api.app.jobs.tick", "--now", post_deadline_time]

    # Run tick
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0

    # 1. Check sv001 (was PUBLISHED, now ACCEPTED_AUTO)
    api_client.logout()
    api_client.login_as_student("sv001")
    sv1_case = api_client.get("/api/v1/student/current").json().get("case", {})
    assert sv1_case.get("status") == "ACCEPTED_AUTO"

    # Kiểm tra acceptance_source trong database
    db = SessionLocal()
    try:
        c1_db = db.query(Case).filter(Case.id == sv1_case["id"]).first()
        assert c1_db.acceptance_source == "TIMEOUT"

        # 2. Check sv002 (was APPEALED, must NOT be auto-accepted)
        api_client.logout()
        api_client.login_as_student("sv002")
        sv2_case = api_client.get("/api/v1/student/current").json().get("case", {})
        assert sv2_case.get("status") == "APPEALED"

        # 3. Check sv003 (was explicitly ACCEPTED, must remain EXPLICIT)
        api_client.logout()
        api_client.login_as_student("sv003")
        sv3_case = api_client.get("/api/v1/student/current").json().get("case", {})
        assert sv3_case.get("status") == "ACCEPTED"
        c3_db = db.query(Case).filter(Case.id == sv3_case["id"]).first()
        assert c3_db.acceptance_source == "EXPLICIT"
    finally:
        db.close()
