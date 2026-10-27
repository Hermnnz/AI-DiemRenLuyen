import hashlib
from decimal import Decimal

from api.app.models.entities import Claim, EvidenceFile
from api.app.services.score_decision_service import evaluate_score_suggestions
from api.app.services.template_service import CRITERIA_49K14_1_DEFINITIONS
from api.tests.conftest import login_helper


DEFINITIONS = {item["code"]: item for item in CRITERIA_49K14_1_DEFINITIONS}


def _set_criterion(criterion, code, *, section_cap=None):
    source = DEFINITIONS[code]
    criterion.code = code
    criterion.title = source["title"]
    criterion.description = source["description"]
    criterion.max_score = source["max_score"]
    criterion.requires_evidence = source["requires_evidence"]
    criterion.rule_config = source["rule_config"]
    criterion.section_code = source["section_code"] if section_cap is not None else None
    criterion.section_max_score = section_cap


def test_score_draft_waits_for_evidence_and_cadre_review_without_mutating_approved(db, seed_data):
    campaign = seed_data["campaign"]
    campaign.template_code = "49K14_1_V1"
    case = seed_data["cases"][0]
    case.status = "BCS_REVIEW"
    first, second, third = seed_data["criteria"]
    for criterion, code in zip((first, second, third), ("4a", "4b_nckh", "8b")):
        _set_criterion(criterion, code)
    claims = {claim.criterion_id: claim for claim in db.query(Claim).filter(Claim.case_id == case.id).all()}
    claims[first.id].self_score = Decimal("4.00")
    claims[second.id].self_score = Decimal("2.00")
    claims[third.id].self_score = Decimal("1.00")
    data = b"evidence"
    file = EvidenceFile(
        claim_id=claims[second.id].id, storage_key="test.png", original_name="test.png",
        mime_type="image/png", size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
        uploaded_by=case.student_id, version_no=1, is_current=True,
    )
    db.add(file)
    db.commit()

    before = evaluate_score_suggestions(db, case)
    items = {item["criterion_code"]: item for item in before["items"]}
    assert items["4a"]["draft_score"] == "4.00"
    assert items["4b_nckh"]["draft_score"] is None
    assert items["8b"]["draft_score"] is None
    assert before["draft_total"] is None

    supported = {"evidence_file_id": file.id, "sha256": file.sha256,
                 "criterion_code": "4b_nckh", "verdict": "SUPPORTED",
                 "authenticity": "UNVERIFIED", "citations": [{"page": 1, "source_excerpt": "x"}]}
    after = evaluate_score_suggestions(db, case, assessments=[supported])
    items = {item["criterion_code"]: item for item in after["items"]}
    assert items["4b_nckh"]["draft_score"] == "2.00"
    assert items["8b"]["status"] == "REVIEW_REQUIRED"
    assert all(claim.approved_score is None for claim in claims.values())
    assert case.status == "BCS_REVIEW"


def test_score_draft_checks_gpa_and_section_cap(db, seed_data):
    seed_data["campaign"].template_code = "49K14_1_V1"
    case = seed_data["cases"][0]
    first, second, third = seed_data["criteria"]
    _set_criterion(first, "4e")
    _set_criterion(second, "4a", section_cap=Decimal("4.00"))
    _set_criterion(third, "4d", section_cap=Decimal("4.00"))
    claims = {claim.criterion_id: claim for claim in db.query(Claim).filter(Claim.case_id == case.id).all()}
    claims[first.id].academic_gpa = Decimal("3.20")
    claims[first.id].self_score = Decimal("4.00")
    claims[second.id].self_score = Decimal("4.00")
    claims[third.id].self_score = Decimal("2.00")
    db.commit()

    result = evaluate_score_suggestions(db, case)
    items = {item["criterion_code"]: item for item in result["items"]}
    assert items["4e"]["draft_score"] == "4.00"
    assert items["4e"]["calculation"] == "GPA 3.20 → 4.00 điểm"
    assert result["draft_total"] is None
    assert items["4a"]["draft_score"] is None
    assert items["4d"]["draft_score"] is None
    assert result["section_checks"][0]["over_cap"] is True

    claims[first.id].self_score = Decimal("2.00")
    db.commit()
    mismatch = evaluate_score_suggestions(db, case)
    assert next(item for item in mismatch["items"] if item["criterion_code"] == "4e")["draft_score"] is None


def test_score_suggestions_api_is_bcs_only_and_does_not_save_scores(client, seed_data, db):
    case = seed_data["cases"][0]
    case.status = "BCS_REVIEW"
    db.commit()
    bcs = login_helper(client, "bcs001")
    student = login_helper(client, "sv001")
    other_bcs = login_helper(client, "bcs_other")
    path = f"/api/v1/bcs/cases/{case.id}/score-suggestions"
    assert client.get(path, cookies=student["cookies"]).status_code == 403
    assert client.get(path, cookies=other_bcs["cookies"]).status_code == 403
    response = client.get(path, cookies=bcs["cookies"])
    assert response.status_code == 200
    assert response.json()["requires_bcs_approval"] is True
    assert response.json()["draft_total"] is None  # Demo rubric is not approved for suggestions.
    assert case.proposed_total is None
