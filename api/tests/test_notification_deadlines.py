from datetime import datetime, timedelta, timezone

import pytest

from api.app.models.entities import Notification, SupplementRequest
from api.app.services.notification_service import format_notification_deadline
from api.app.services.deadline_service import run_deadline_tick
from api.tests.conftest import login_helper


@pytest.mark.parametrize("value", [
    datetime(2026, 11, 3, 18, 5),
    datetime(2026, 11, 3, 18, 5, tzinfo=timezone.utc),
    datetime(2026, 11, 4, 1, 5, tzinfo=timezone(timedelta(hours=7))),
    datetime(2026, 11, 3, 13, 5, tzinfo=timezone(timedelta(hours=-5))),
])
def test_notification_deadline_handles_utc_offsets_and_day_rollover(value):
    assert format_notification_deadline(value) == "04/11/2026 01:05 (giờ Việt Nam, UTC+7)"


def test_reminder_uses_vietnam_time_without_changing_stored_deadline(seed_data, db):
    now = datetime(2026, 11, 3, 17, 0, tzinfo=timezone.utc)
    campaign = seed_data["campaign"]
    campaign.status = "PUBLISHED"
    campaign.published_at = now - timedelta(hours=49)
    campaign.appeal_deadline_at = datetime(2026, 11, 3, 18, 5, tzinfo=timezone.utc)
    case = seed_data["cases"][0]
    case.status = "PUBLISHED"
    case.published_at = campaign.published_at
    case.appeal_deadline_at = campaign.appeal_deadline_at
    db.commit()
    result = run_deadline_tick(db, now)
    assert result["reminded_cases"] == 1
    note = db.query(Notification).filter_by(type="APPEAL_REMINDER", user_id=case.student_id).one()
    assert "04/11/2026 01:05 (giờ Việt Nam, UTC+7)" in note.body
    db.refresh(case)
    assert case.appeal_deadline_at.replace(tzinfo=timezone.utc) == campaign.appeal_deadline_at.replace(tzinfo=timezone.utc)
    assert case.status == "PUBLISHED"
    assert run_deadline_tick(db, now)["reminded_cases"] == 0


def test_missing_evidence_notification_formats_its_actual_deadline(client, seed_data, db):
    from api.app.models.entities import Claim

    case = seed_data["cases"][0]
    for claim in db.query(Claim).filter_by(case_id=case.id):
        claim.self_score = 1 if claim.criterion.requires_evidence else 0
    db.commit()
    auth = login_helper(client, "sv001")
    response = client.post(f"/api/v1/student/cases/{case.id}/submit",
                          json={"expected_version": case.version},
                          cookies=auth["cookies"], headers=auth["headers"])
    assert response.status_code == 200 and response.json()["status"] == "NEEDS_INFO"
    request = db.query(SupplementRequest).filter_by(case_id=case.id, kind="INFO").one()
    note = db.query(Notification).filter_by(case_id=case.id, type="NEEDS_INFO").one()
    utc = request.deadline_at.replace(tzinfo=timezone.utc)
    expected = (utc + timedelta(hours=7)).strftime("%d/%m/%Y %H:%M")
    assert expected + " (giờ Việt Nam, UTC+7)" in note.body
