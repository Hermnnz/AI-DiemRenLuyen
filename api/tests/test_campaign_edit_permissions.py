from datetime import datetime, timezone, timedelta
from decimal import Decimal

from api.app.models.entities import AuditEvent, Claim, Criterion, EvidenceFile
from api.tests.conftest import login_helper


def _payload(campaign, criteria):
    return {
        "class_id": campaign.class_id,
        "title": campaign.title,
        "term": campaign.term,
        "template_code": campaign.template_code,
        "open_at": campaign.open_at.isoformat(),
        "submission_deadline_at": campaign.submission_deadline_at.isoformat(),
        "supplement_period_hours": campaign.supplement_period_hours,
        "appeal_period_hours": campaign.appeal_period_hours,
        "reminder_after_hours": campaign.reminder_after_hours,
        "max_info_rounds": campaign.max_info_rounds,
        "max_proof_rounds": campaign.max_proof_rounds,
        "criteria": [
            {"id": c.id, "code": c.code, "title": c.title, "description": c.description,
             "max_score": str(c.max_score), "requires_evidence": c.requires_evidence,
             "sort_order": c.sort_order, "section_code": c.section_code,
             "section_title": c.section_title, "section_max_score": str(c.section_max_score) if c.section_max_score else None,
             "evidence_notes": c.evidence_notes, "allowed_input_roles": c.allowed_input_roles,
             "rule_config": c.rule_config}
            for c in criteria
        ],
    }


def test_bcs_can_open_own_draft_only(client, db, seed_data):
    campaign = seed_data["campaign"]
    campaign.status = "DRAFT"
    db.commit()
    other_bcs = login_helper(client, "bcs_other")
    denied = client.post(f"/api/v1/bcs/campaigns/{campaign.id}/open", headers=other_bcs["headers"], cookies=other_bcs["cookies"])
    assert denied.status_code == 403
    student = login_helper(client, "sv001")
    denied = client.post(f"/api/v1/bcs/campaigns/{campaign.id}/open", headers=student["headers"], cookies=student["cookies"])
    assert denied.status_code == 403
    bcs = login_helper(client, "bcs001")
    opened = client.post(f"/api/v1/bcs/campaigns/{campaign.id}/open", headers=bcs["headers"], cookies=bcs["cookies"])
    assert opened.status_code == 200, opened.text
    assert opened.json()["status"] == "OPEN"
    assert db.query(AuditEvent).filter(AuditEvent.campaign_id == campaign.id, AuditEvent.action == "CAMPAIGN_OPENED").count() == 1


def test_admin_edits_open_campaign_without_losing_claims_or_evidence(client, db, seed_data):
    campaign = seed_data["campaign"]
    criteria = seed_data["criteria"]
    case = seed_data["cases"][0]
    claim = db.query(Claim).filter(Claim.case_id == case.id, Claim.criterion_id == criteria[0].id).one()
    claim.self_score = Decimal("3.00")
    case.status = "PROPOSED"
    case.proposed_total = Decimal("3.00")
    evidence = EvidenceFile(
        claim_id=claim.id, storage_key="campaign-edit-test-evidence", original_name="test.png",
        mime_type="image/png", size_bytes=4, sha256="0" * 64, uploaded_by=case.student_id,
        uploaded_at=datetime.now(timezone.utc),
    )
    db.add(evidence)
    db.commit()

    admin = login_helper(client, "admin001")
    listed = client.get("/api/v1/admin/campaigns", headers=admin["headers"], cookies=admin["cookies"])
    assert listed.status_code == 200
    assert "rule_config" in listed.json()[0]["criteria"][0]
    payload = _payload(campaign, criteria)
    payload["title"] = "Đợt đã sửa"
    payload["criteria"][0]["title"] = "Tiêu chí đã cập nhật"
    payload["criteria"].append({"code": "TC04", "title": "Tiêu chí mới", "max_score": "5.00", "sort_order": 4})
    changed = client.put(f"/api/v1/admin/campaigns/{campaign.id}", json=payload, headers=admin["headers"], cookies=admin["cookies"])
    assert changed.status_code == 200, changed.text
    assert changed.json()["status"] == "OPEN"
    assert changed.json()["criteria"][0]["id"] == criteria[0].id
    assert db.query(EvidenceFile).filter(EvidenceFile.id == evidence.id).count() == 1
    assert db.query(Claim).filter(Claim.id == claim.id).one().self_score == Decimal("3.00")
    assert case.status == "BCS_REVIEW"
    assert case.proposed_total is None
    new_criterion = db.query(Criterion).filter(Criterion.campaign_id == campaign.id, Criterion.code == "TC04").one()
    assert db.query(Claim).filter(Claim.criterion_id == new_criterion.id).count() == len(seed_data["cases"])

    payload["criteria"] = payload["criteria"][1:]
    rejected = client.put(f"/api/v1/admin/campaigns/{campaign.id}", json=payload, headers=admin["headers"], cookies=admin["cookies"])
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "CRITERION_HAS_DATA"


def test_admin_cannot_move_open_campaign_to_other_class(client, db, seed_data):
    admin = login_helper(client, "admin001")
    payload = _payload(seed_data["campaign"], seed_data["criteria"])
    payload["class_id"] = seed_data["class_other"].id
    response = client.put(f"/api/v1/admin/campaigns/{seed_data['campaign'].id}", json=payload, headers=admin["headers"], cookies=admin["cookies"])
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CLASS_CHANGE_FORBIDDEN"


def test_bcs_schedules_then_opens_when_due(client, db, seed_data):
    campaign = seed_data["campaign"]
    campaign.status = "DRAFT"
    campaign.open_at = datetime.now(timezone.utc) + timedelta(hours=1)
    db.commit()
    bcs = login_helper(client, "bcs001")
    url = f"/api/v1/bcs/campaigns/{campaign.id}/open"
    scheduled = client.post(url, headers=bcs["headers"], cookies=bcs["cookies"])
    assert scheduled.status_code == 200
    assert scheduled.json()["status"] == "SCHEDULED"
    early = client.post(url, headers=bcs["headers"], cookies=bcs["cookies"])
    assert early.status_code == 409
    campaign.open_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()
    opened = client.post(url, headers=bcs["headers"], cookies=bcs["cookies"])
    assert opened.status_code == 200
    assert opened.json()["status"] == "OPEN"
