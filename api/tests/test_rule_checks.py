from datetime import date
from decimal import Decimal

from api.app.models.entities import Claim, Criterion, EvidenceFile
from api.app.services.rule_check_service import evaluate_case_rules
from api.tests.conftest import login_helper


def _file(claim, case, key, digest, name="certificate.png"):
    return EvidenceFile(
        claim_id=claim.id, storage_key=key, original_name=name,
        mime_type="image/png", size_bytes=100, sha256=digest,
        uploaded_by=case.student_id, version_no=1, is_current=True,
    )


def test_rules_use_hash_and_4b_exception_without_automatic_score_change(seed_data, db):
    case = seed_data["cases"][0]
    campaign = seed_data["campaign"]
    campaign.template_code = "49K14_1_V1"
    claim_a = db.query(Claim).filter(Claim.case_id == case.id, Claim.criterion_id == seed_data["criteria"][0].id).one()
    claim_c = db.query(Claim).filter(Claim.case_id == case.id, Claim.criterion_id == seed_data["criteria"][2].id).one()
    claim_a.self_score = Decimal("2.00")
    claim_c.self_score = Decimal("2.00")
    four_b = Criterion(campaign_id=campaign.id, code="4b_nckh", title="NCKH", max_score=Decimal("2.00"),
                       requires_evidence=True, sort_order=4)
    db.add(four_b)
    db.flush()
    claim_b = Claim(case_id=case.id, criterion_id=four_b.id, self_score=Decimal("1.00"))
    db.add(claim_b)
    db.flush()
    db.add_all([
        _file(claim_a, case, "a.png", "a" * 64),
        _file(claim_c, case, "c.png", "a" * 64),
        _file(claim_b, case, "b.png", "a" * 64),
    ])
    db.commit()

    result = evaluate_case_rules(db, case)
    duplicate = next(item for item in result["findings"] if item["code"] == "DUPLICATE_EVIDENCE")
    assert duplicate["details"]["criterion_codes"] == ["TC01", "TC03"]
    assert claim_a.approved_score is None

    # A matching filename with different bytes is not a duplicate.
    for file in db.query(EvidenceFile).filter(EvidenceFile.storage_key == "c.png"):
        file.sha256 = "c" * 64
    db.commit()
    assert not any(item["code"] == "DUPLICATE_EVIDENCE" for item in evaluate_case_rules(db, case)["findings"])


def test_rules_flag_8b_review_missing_evidence_and_extracted_date(seed_data, db):
    case = seed_data["cases"][0]
    campaign = seed_data["campaign"]
    campaign.template_code = "49K14_1_V1"
    campaign.term_start_on = date(2025, 9, 1)
    campaign.term_end_on = date(2026, 1, 31)
    eight_b = Criterion(campaign_id=campaign.id, code="8b", title="Kỹ năng tổ chức",
                        max_score=Decimal("3.00"), requires_evidence=True, sort_order=4,
                        rule_config={"type": "OPTIONS", "mandatory_bcs_review_if_positive": True,
                                     "options": [{"score": "0.00"}, {"score": "1.00"}, {"score": "2.00"}]})
    db.add(eight_b)
    db.flush()
    claim = Claim(case_id=case.id, criterion_id=eight_b.id, self_score=Decimal("3.00"))
    db.add(claim)
    db.flush()
    initial = evaluate_case_rules(db, case)
    codes = {item["code"] for item in initial["findings"]}
    assert {"SCORE_OUT_OF_RANGE", "SCORE_LEVEL_NOT_ALLOWED", "EVIDENCE_MISSING", "MANDATORY_BCS_REVIEW"} <= codes

    evidence = _file(claim, case, "eight-b.png", "b" * 64)
    db.add(evidence)
    db.commit()
    read = [{"evidence_file_id": evidence.id, "sha256": evidence.sha256, "readable": True,
             "facts": [{"kind": "event_date", "value": "Ngày 02/02/2026", "page": 1,
                        "source_excerpt": "02/02/2026"}]}]
    result = evaluate_case_rules(db, case, read)
    assert any(item["code"] == "EVENT_DATE_OUTSIDE_TERM" for item in result["findings"])
    assert not any(item["code"] == "EVIDENCE_MISSING" for item in result["findings"])
    assert claim.approved_score is None


def test_rule_api_is_scoped_to_own_case_and_class(client, seed_data, db):
    case = seed_data["cases"][0]
    bcs = login_helper(client, "bcs001")
    other_bcs = login_helper(client, "bcs_other")
    student = login_helper(client, "sv001")
    other_student = login_helper(client, "sv002")
    bcs_path = f"/api/v1/bcs/cases/{case.id}/rule-checks"
    student_path = f"/api/v1/student/cases/{case.id}/rule-checks"
    assert client.get(bcs_path, cookies=bcs["cookies"]).status_code == 200
    assert client.get(bcs_path, cookies=other_bcs["cookies"]).status_code == 403
    assert client.get(student_path, cookies=student["cookies"]).status_code == 200
    assert client.get(student_path, cookies=other_student["cookies"]).status_code == 404


def test_admin_sets_term_window_without_losing_template_rules(client, seed_data):
    admin = login_helper(client, "admin001")
    payload = {
        "class_id": seed_data["class_demo"].id,
        "title": "Đợt kiểm tra luật",
        "term": "HK1-2025-2026",
        "template_code": "49K14_1_V1",
        "term_start_on": "2025-09-01",
        "term_end_on": "2026-01-31",
        "open_at": "2026-02-01T00:00:00Z",
        "submission_deadline_at": "2026-02-15T00:00:00Z",
        "criteria": [],
    }
    path = "/api/v1/admin/campaigns"
    partial = client.post(path, json={**payload, "term_end_on": None},
                          cookies=admin["cookies"], headers=admin["headers"])
    assert partial.status_code == 422
    created = client.post(path, json=payload, cookies=admin["cookies"], headers=admin["headers"])
    assert created.status_code == 201
    campaign_id = created.json()["id"]
    assert created.json()["term_start_on"] == "2025-09-01"
    details = client.get(path + f"/{campaign_id}", cookies=admin["cookies"]).json()
    eight_b = next(item for item in details["criteria"] if item["code"] == "8b")
    assert eight_b["rule_config"]["mandatory_bcs_review_if_positive"] is True

    # The existing admin form sends only basic criterion fields on save.
    basic_criteria = [{key: item[key] for key in ("code", "title", "description", "max_score",
                                                    "requires_evidence", "sort_order")}
                      for item in details["criteria"]]
    updated = client.put(path + f"/{campaign_id}",
                         json={**payload, "term_end_on": "2026-02-01", "criteria": basic_criteria},
                         cookies=admin["cookies"], headers=admin["headers"])
    assert updated.status_code == 200
    details = client.get(path + f"/{campaign_id}", cookies=admin["cookies"]).json()
    assert details["term_end_on"] == "2026-02-01"
    eight_b = next(item for item in details["criteria"] if item["code"] == "8b")
    assert eight_b["rule_config"]["mandatory_bcs_review_if_positive"] is True
