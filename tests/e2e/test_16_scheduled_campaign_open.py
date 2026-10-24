"""
Acceptance Test 16 - Section 9.16:
Đợt SCHEDULED chưa tạo case/chưa cho nộp; tick ở open_at tạo đúng một case mỗi SV, chạy lặp lại không tạo trùng.
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


def test_16_scheduled_campaign_open_and_case_initialization_idempotency(api_client: AcceptanceTestClient):
    """
    Kịch bản:
    1. Đợt ở trạng thái SCHEDULED (open_at ở tương lai).
    2. Trong trạng thái SCHEDULED:
       - Chưa có case nào được tạo cho sinh viên trong cơ sở dữ liệu.
    3. Thời gian giả lập đến mốc mở đợt (now >= open_at).
    4. Chạy lệnh deadline tick:
       - Đợt chuyển từ SCHEDULED sang OPEN; opened_at = NOW().
       - Tự động khởi tạo đúng 1 hồ sơ (case) ở trạng thái DRAFT cho mỗi sinh viên trong lớp (sv001, sv002, sv003).
    5. Chạy lặp lại deadline tick lần 2:
       - Tính idempotent được bảo toàn: Không tạo thêm case trùng lặp (duy trì đúng 1 case/sinh viên).
    """
    from api.app.database import SessionLocal
    from api.app.models.entities import Campaign, Case, Claim

    open_time = datetime(2026, 10, 25, 1, 0, 0, tzinfo=timezone.utc)

    # 1. Chuẩn bị: Đặt đợt về SCHEDULED và xóa sạch cases
    db = SessionLocal()
    try:
        camp = db.query(Campaign).first()
        camp.status = "SCHEDULED"
        camp.open_at = open_time
        db.query(Claim).delete()
        db.query(Case).delete()
        db.commit()
    finally:
        db.close()

    # Kiểm tra ban đầu: chưa có case nào
    db = SessionLocal()
    try:
        assert db.query(Case).count() == 0
    finally:
        db.close()

    # 2. Trigger tick at open_at
    simulated_open_time = "2026-10-25T01:00:00Z"
    cmd = [sys.executable, "-m", "api.app.jobs.tick", "--now", simulated_open_time]

    # Run tick 1st time
    p1 = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    assert p1.returncode == 0

    # 3. Verify students have exactly 1 draft case
    for sv in ["sv001", "sv002", "sv003"]:
        api_client.logout()
        api_client.login_as_student(sv)
        current = api_client.get("/api/v1/student/current").json()
        assert current.get("case") is not None
        assert current["case"]["status"] == "DRAFT"

    # 4. Run tick 2nd time (Idempotency test)
    p2 = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    assert p2.returncode == 0

    # Check again: still exactly 1 case per student
    db = SessionLocal()
    try:
        assert db.query(Case).count() == 3
    finally:
        db.close()

    for sv in ["sv001", "sv002", "sv003"]:
        api_client.logout()
        api_client.login_as_student(sv)
        current = api_client.get("/api/v1/student/current").json()
        assert current["case"]["status"] == "DRAFT"
