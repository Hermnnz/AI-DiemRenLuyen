import pytest
from datetime import datetime, timezone, timedelta
from api.tests.conftest import login_helper
from api.app.models.entities import Campaign, Case, Criterion, Notification, ClassMember
from api.app.services.deadline_service import run_deadline_tick
from api.app.jobs.tick import run_tick


def test_acceptance_criteria_16_scheduled_campaign_and_tick_open(client, seed_data, db):
    """
    Tiêu chí 16: Đợt SCHEDULED chưa tạo case/chưa cho nộp;
    tick ở open_at tạo đúng một case mỗi SV, chạy lặp lại không tạo trùng.
    """
    auth_admin = login_helper(client, "admin001")
    cls_demo = seed_data["class_demo"]

    now = datetime.now(timezone.utc)
    future_open = now + timedelta(days=2)
    future_deadline = now + timedelta(days=7)

    # 1. Admin creates a new campaign
    resp_create = client.post(
        "/api/v1/admin/campaigns",
        json={
            "class_id": cls_demo.id,
            "title": "Đợt Học Kỳ 2 2026",
            "term": "HK2-2026",
            "open_at": future_open.isoformat(),
            "submission_deadline_at": future_deadline.isoformat(),
            "supplement_period_hours": 48,
            "appeal_period_hours": 72,
            "reminder_after_hours": 48,
            "max_info_rounds": 2,
            "max_proof_rounds": 2,
            "criteria": [
                {"code": "TC01", "title": "Tiêu chí 1", "max_score": "10.00", "requires_evidence": True, "sort_order": 1}
            ],
        },
        cookies=auth_admin["cookies"],
        headers=auth_admin["headers"],
    )
    assert resp_create.status_code == 201
    camp_id = resp_create.json()["id"]

    # 2. Admin calls open endpoint while open_at is in the future -> transitions to SCHEDULED
    resp_open = client.post(
        f"/api/v1/admin/campaigns/{camp_id}/open",
        cookies=auth_admin["cookies"],
        headers=auth_admin["headers"],
    )
    assert resp_open.status_code == 200
    assert resp_open.json()["status"] == "SCHEDULED"

    # Verify no cases exist for this campaign yet
    cases_count_before = db.query(Case).filter(Case.campaign_id == camp_id).count()
    assert cases_count_before == 0

    # 3. Run tick before open_at (at now + 1 day) -> campaign remains SCHEDULED, 0 cases created
    tick_before = now + timedelta(days=1)
    stats1 = run_deadline_tick(db, tick_before)
    assert stats1["opened_campaigns"] == 0
    assert db.query(Case).filter(Case.campaign_id == camp_id).count() == 0

    # 4. Run tick at or after open_at (at future_open + 1 hour) -> campaign transitions to OPEN, exactly 1 case created per student (3 students)
    tick_at_open = future_open + timedelta(hours=1)
    stats2 = run_deadline_tick(db, tick_at_open)
    assert stats2["opened_campaigns"] == 1
    camp_opened = db.query(Campaign).filter(Campaign.id == camp_id).first()
    assert camp_opened.status == "OPEN"
    cases_count_after = db.query(Case).filter(Case.campaign_id == camp_id).count()
    assert cases_count_after == 3

    # 5. Run tick again at same or later time -> Idempotent! Does not create duplicate cases
    stats3 = run_deadline_tick(db, tick_at_open + timedelta(minutes=5))
    assert stats3["opened_campaigns"] == 0
    assert db.query(Case).filter(Case.campaign_id == camp_id).count() == 3


def test_submission_deadline_timeout_draft_to_closed_no_submit(seed_data, db):
    """
    Quá hạn nộp hồ sơ: OPEN -> REVIEW, DRAFT -> CLOSED_NO_SUBMIT
    """
    camp = seed_data["campaign"]
    cases = seed_data["cases"]

    # All 3 cases are in DRAFT
    assert all(c.status == "DRAFT" for c in cases)

    # Run tick past submission_deadline_at
    past_sub_dl = camp.submission_deadline_at.replace(tzinfo=timezone.utc) + timedelta(hours=1)
    stats = run_deadline_tick(db, past_sub_dl)

    assert stats["reviewed_campaigns"] >= 1
    assert stats["closed_no_submit_cases"] == 3

    # All cases are now CLOSED_NO_SUBMIT
    for c in cases:
        db.refresh(c)
        assert c.status == "CLOSED_NO_SUBMIT"


def test_acceptance_criteria_12_and_13_tick_idempotency_and_auto_accept(seed_data, db):
    """
    Tiêu chí 12: Deadline tick chạy hai lần không gửi trùng thông báo và không tăng lượt hai lần.
    Tiêu chí 13: Quá hạn phản hồi mà SV chưa đồng ý/khiếu nại thì thành ACCEPTED_AUTO đúng một lần;
    SV đã phản hồi không bị tự chấp nhận.
    """
    camp = seed_data["campaign"]
    now = datetime.now(timezone.utc)
    camp.status = "PUBLISHED"
    camp.published_at = now - timedelta(hours=50)
    camp.appeal_deadline_at = now + timedelta(hours=22)  # 50 + 22 = 72h total appeal period
    camp.reminder_after_hours = 48

    # Case 0: Responded (ACCEPTED)
    case0 = seed_data["cases"][0]
    case0.status = "ACCEPTED"
    case0.acceptance_source = "EXPLICIT"
    case0.published_at = camp.published_at
    case0.appeal_deadline_at = camp.appeal_deadline_at

    # Case 1: Not responded (still PUBLISHED)
    case1 = seed_data["cases"][1]
    case1.status = "PUBLISHED"
    case1.published_at = camp.published_at
    case1.appeal_deadline_at = camp.appeal_deadline_at

    # Case 2: Appealed (APPEALED)
    case2 = seed_data["cases"][2]
    case2.status = "APPEALED"
    case2.published_at = camp.published_at
    case2.appeal_deadline_at = camp.appeal_deadline_at

    db.commit()

    # 1. Tick at now (50 hours after publish, which is > 48h reminder_after_hours, but < appeal_deadline_at)
    # Only Case 1 should get a reminder notification. Case 0 and Case 2 already responded!
    stats1 = run_deadline_tick(db, now)
    assert stats1["reminded_cases"] == 1

    notifs_remind = db.query(Notification).filter(Notification.type == "APPEAL_REMINDER").all()
    assert len(notifs_remind) == 1
    assert notifs_remind[0].user_id == case1.student_id

    # Run tick AGAIN at now -> Idempotency! 0 extra notifications
    stats1_repeat = run_deadline_tick(db, now)
    assert stats1_repeat["reminded_cases"] == 0
    assert db.query(Notification).filter(Notification.type == "APPEAL_REMINDER").count() == 1

    # 2. Tick past appeal_deadline_at
    future_past_appeal = camp.appeal_deadline_at + timedelta(hours=1)
    stats2 = run_deadline_tick(db, future_past_appeal)

    # Only Case 1 (unresponded) should transition to ACCEPTED_AUTO
    assert stats2["auto_accepted_cases"] == 1
    db.refresh(case0)
    db.refresh(case1)
    db.refresh(case2)

    assert case0.status == "ACCEPTED"
    assert case0.acceptance_source == "EXPLICIT"

    assert case1.status == "ACCEPTED_AUTO"
    assert case1.acceptance_source == "TIMEOUT"

    assert case2.status == "APPEALED"

    # Run tick past appeal deadline AGAIN -> Idempotency!
    stats2_repeat = run_deadline_tick(db, future_past_appeal + timedelta(minutes=10))
    assert stats2_repeat["auto_accepted_cases"] == 0
    assert db.query(Notification).filter(Notification.type == "ACCEPTED_AUTO").count() == 1
