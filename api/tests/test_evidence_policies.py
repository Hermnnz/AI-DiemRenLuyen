from datetime import date
from decimal import Decimal

import pytest

from api.app.models.entities import AiReviewRun, Claim
from api.app.review.evidence_policy import (
    ACTIVITY, BLOOD_DONATION, INSURANCE, SOCIAL_POST,
    identity_matches, policy_for, policy_issues, required_facts_present,
)
from api.app.review.gemini_read import ReadContent
from api.app.services.template_service import CRITERIA_49K14_1_DEFINITIONS
from api.tests.conftest import login_helper
from api.tests.test_automatic_ai_submission import automatic_submission


START, END = date(2026, 1, 1), date(2026, 11, 30)
DEFINITIONS = {item["code"]: item for item in CRITERIA_49K14_1_DEFINITIONS}


def fact(kind, value, source=None):
    return {"kind": kind, "value": value, "page": 1, "source_excerpt": source or value}


def insurance_facts(name="Nguyễn Văn A", start="2026-01-01", end=None):
    facts = [fact("document_type", "Thẻ BHYT", "THẺ BẢO HIỂM Y TẾ"),
             fact("recipient", name), fact("issuer", "Bảo hiểm xã hội Việt Nam"),
             fact("reference_code", "TEST-INSURANCE-001"),
             fact("valid_from", start, f"Giá trị sử dụng từ ngày {start}"),
             fact("issued_on", "2025-12-27"), fact("birth_date", "2005-08-04")]
    if end is not None:
        facts.append(fact("valid_until", end, f"Giá trị sử dụng đến ngày {end}"))
    return facts


def post_facts(name="Nguyễn Văn A", post_date="2026-09-06"):
    return [fact("document_type", "Ảnh bài đăng Facebook"), fact("account_name", name),
            fact("post_content", "Tuyên truyền phòng chống tội phạm"),
            fact("source_name", "Phòng Công tác sinh viên"), fact("post_date", post_date)]


def blood_facts(name="Nguyễn Văn A"):
    return [fact("document_type", "Giấy chứng nhận hiến máu"), fact("recipient", name),
            fact("issuer", "Trung tâm hiến máu"), fact("event_date", "2026-09-20"),
            fact("issued_on", "2025-12-27"), fact("birth_date", "2005-08-04")]


@pytest.mark.parametrize("start,end,code", [
    ("2026-01-01", None, None),
    ("2025-12-01", "2026-06-30", None),
    ("2026-11-30", None, None),
    ("2025-01-01", "2026-01-01", None),
    ("2025-01-01", None, "INSURANCE_COVERAGE_UNCONFIRMED"),
    ("2025-01-01", "2025-12-31", "INSURANCE_OUTSIDE_TERM"),
    ("2026-12-01", None, "INSURANCE_OUTSIDE_TERM"),
    ("2026-01-01", "2025-12-31", "INSURANCE_VALIDITY_INVALID"),
    ("01/2026", None, "INSURANCE_VALIDITY_AMBIGUOUS"),
    ("2026-01-01", "31/02/2026", "INSURANCE_VALIDITY_AMBIGUOUS"),
])
def test_insurance_checks_coverage_instead_of_issue_or_birth_date(start, end, code):
    facts = insurance_facts(start=start, end=end)
    policy = policy_for("7a2", facts, "49K14_1_V1")
    issues = policy_issues(policy, facts, START, END)
    assert policy == INSURANCE
    assert [item["code"] for item in issues] == ([code] if code else [])
    assert required_facts_present(policy, facts)
    assert "activity_name" not in {item["kind"] for item in facts}


def test_insurance_never_falls_back_to_the_signed_date_or_legacy_event_date():
    facts = [item for item in insurance_facts() if item["kind"] != "valid_from"]
    facts.append(fact("event_date", "2026-01-01"))
    issues = policy_issues(INSURANCE, facts, START, END)
    assert issues[0]["code"] == "INSURANCE_VALID_FROM_NOT_FOUND"
    assert not required_facts_present(INSURANCE, facts)


def test_insurance_detects_conflicting_coverage_and_wrong_type():
    facts = insurance_facts() + [fact("valid_from", "2025-01-01")]
    assert policy_issues(INSURANCE, facts, START, END)[0]["code"] == "INSURANCE_VALIDITY_AMBIGUOUS"
    facts = insurance_facts()
    facts[0] = fact("document_type", "Giấy chứng nhận tham gia hoạt động")
    assert policy_for("7a2", facts, "49K14_1_V1") == INSURANCE
    assert policy_issues(INSURANCE, facts, START, END)[0]["code"] == "EVIDENCE_TYPE_MISMATCH"


def test_policy_cannot_be_weakened_by_a_model_label_on_an_unrelated_criterion():
    assert policy_for("6c", insurance_facts(), "49K14_1_V1") == ACTIVITY
    assert policy_for("7a2", insurance_facts(), "CUSTOM_TEMPLATE") == ACTIVITY
    assert policy_for("6c", blood_facts(), "49K14_1_V1") == ACTIVITY


def test_posts_use_post_time_and_source_without_requiring_a_certificate_issuer():
    facts = post_facts() + [fact("event_date", "2024-02-01"), fact("issued_on", "2024-02-01")]
    facts[0] = fact("document_type", "Ảnh bài đăng Facebook", "Nguyễn Văn A đã chia sẻ một bài viết")
    assert policy_for("6c", facts, "49K14_1_V1") == SOCIAL_POST
    assert required_facts_present(SOCIAL_POST, facts)
    assert not policy_issues(SOCIAL_POST, facts, START, END)
    assert identity_matches(SOCIAL_POST, facts, "NGUYEN VAN A")
    assert not identity_matches(SOCIAL_POST, post_facts(name="Văn A"), "Nguyễn Văn A")
    assert policy_issues(SOCIAL_POST, post_facts(post_date="6 tháng 9"), START, END)[0]["code"] == "POST_DATE_AMBIGUOUS"
    assert policy_issues(SOCIAL_POST, post_facts(post_date="2025-09-06"), START, END)[0]["code"] == "POST_DATE_OUTSIDE_TERM"


def test_donation_title_supplies_activity_type_but_not_identity_or_donation_date():
    facts = blood_facts()
    assert policy_for("7c", facts, "49K14_1_V1") == BLOOD_DONATION
    assert required_facts_present(BLOOD_DONATION, facts)
    assert not policy_issues(BLOOD_DONATION, facts, START, END)
    assert not identity_matches(BLOOD_DONATION, blood_facts(name="Người khác"), "Nguyễn Văn A")
    assert not identity_matches(BLOOD_DONATION, facts + [fact("recipient", "Người khác")], "Nguyễn Văn A")
    facts = [item for item in facts if item["kind"] != "event_date"]
    assert policy_issues(BLOOD_DONATION, facts, START, END)[0]["code"] == "EVENT_DATE_NOT_FOUND"


def test_activity_still_requires_actual_activity_name_and_date():
    facts = [fact("recipient", "Nguyễn Văn A"), fact("activity_name", "Hội thảo A"),
             fact("issuer", "Đoàn trường"), fact("event_date", "2026-09-20"),
             fact("issued_on", "2025-12-27"), fact("birth_date", "2005-08-04")]
    assert required_facts_present(ACTIVITY, facts)
    assert not policy_issues(ACTIVITY, facts, START, END)
    assert not required_facts_present(ACTIVITY, [item for item in facts if item["kind"] != "activity_name"])


def test_ocr_schema_preserves_distinct_date_roles_and_post_fields():
    result = ReadContent.model_validate({"readable": True, "unreadable_reason": "",
                                        "facts": insurance_facts() + post_facts()})
    assert {item.kind for item in result.facts} >= {"valid_from", "issued_on", "birth_date", "post_date", "source_name"}


@pytest.mark.parametrize("kind,accepted", [
    ("insurance", True), ("insurance_old_start_no_end", False),
    ("insurance_expired", False), ("insurance_wrong_type", False),
    ("insurance_wrong_person", False), ("insurance_missing_id", False),
    ("insurance_low_self_confidence", False),
    ("post", True), ("post_alias", False), ("donation", True), ("donation_wrong_person", False),
])
def test_typed_evidence_runs_both_confidence_gates_without_bcs_click(
    client, db, automatic_submission, kind, accepted,
):
    case, evidence, facts, options, calls = automatic_submission
    claim = db.query(Claim).filter_by(id=evidence.claim_id).one()
    code = "7a2" if kind.startswith("insurance") else "6c" if kind.startswith("post") else "7c"
    definition = DEFINITIONS[code]
    criterion = claim.criterion
    for key in ["code", "title", "description", "max_score", "requires_evidence", "evidence_notes", "rule_config"]:
        setattr(criterion, key, definition[key])
    claim.self_score = max(Decimal(str(item["score"])) for item in definition["rule_config"]["options"])
    if code == "7a2":
        facts[:] = insurance_facts(case.student.full_name)
    elif code == "6c":
        facts[:] = post_facts(case.student.full_name)
    else:
        facts[:] = blood_facts(case.student.full_name)
    if kind == "insurance_old_start_no_end":
        facts[:] = insurance_facts(case.student.full_name, start="2025-01-01")
    elif kind == "insurance_expired":
        facts[:] = insurance_facts(case.student.full_name, start="2025-01-01", end="2025-12-31")
    elif kind == "insurance_wrong_type":
        facts[0] = fact("document_type", "Giấy chứng nhận hoạt động")
    elif kind.endswith("wrong_person"):
        facts[1] = fact("recipient", "Người khác")
    elif kind == "post_alias":
        facts[1] = fact("account_name", "Văn A")
    elif kind == "insurance_missing_id":
        facts[:] = [item for item in facts if item["kind"] != "reference_code"]
    elif kind == "insurance_low_self_confidence":
        options["self_confidence"] = 0.6999
    db.commit()
    student = login_helper(client, "sv001")
    response = client.post(f"/api/v1/student/cases/{case.id}/submit",
                           json={"expected_version": case.version},
                           cookies=student["cookies"], headers=student["headers"])
    assert response.status_code == 200
    db.expire_all()
    run = db.query(AiReviewRun).filter_by(case_id=case.id).one()
    assert run.error_code is None
    assert bool(run.result_json["auto_accepted_evidence"]) is accepted
    if accepted:
        assert calls == ["read", "assess", "self_review"]
        assert run.result_json["auto_accepted_evidence"][0]["evidence_type"] in {
            "HEALTH_INSURANCE", "SOCIAL_POST", "BLOOD_DONATION"}
    bcs = login_helper(client, "bcs001")
    detail = client.get(f"/api/v1/bcs/cases/{case.id}", cookies=bcs["cookies"]).json()
    assert (evidence.id not in detail["evidence_review_required_ids"]) is accepted
    assert claim.approved_score is None and case.proposed_total is None


@pytest.mark.parametrize("outdated_field", ["pipeline_version", "auto_accept_threshold"])
def test_old_ai_policy_is_replaced_once_without_a_bcs_analysis_click(client, db, automatic_submission, outdated_field):
    from api.app.services.ai_review_service import PIPELINE_VERSION

    case, _, _, _, calls = automatic_submission
    student = login_helper(client, "sv001")
    response = client.post(f"/api/v1/student/cases/{case.id}/submit", json={"expected_version": case.version},
                           cookies=student["cookies"], headers=student["headers"])
    assert response.status_code == 200
    db.expire_all()
    old = db.query(AiReviewRun).filter_by(case_id=case.id).one()
    old.idempotency_key = f"historical-{outdated_field}"
    old.result_json = {**old.result_json, outdated_field:
                      "gemini-read-transparency-decision-v4" if outdated_field == "pipeline_version" else 0.80}
    db.commit()
    bcs = login_helper(client, "bcs001")
    path = f"/api/v1/bcs/cases/{case.id}/ai-reviews/latest"
    new = client.get(path, cookies=bcs["cookies"]).json()["run"]
    assert new["id"] != old.id
    db.expire_all()
    latest = db.query(AiReviewRun).filter_by(id=new["id"]).one()
    assert latest.result_json["pipeline_version"] == PIPELINE_VERSION
    assert latest.result_json["auto_accept_threshold"] == 0.70
    count = len(calls)
    assert client.get(path, cookies=bcs["cookies"]).json()["run"]["id"] == latest.id
    assert len(calls) == count
