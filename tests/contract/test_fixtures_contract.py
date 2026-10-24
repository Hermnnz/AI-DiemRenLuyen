"""
Contract tests validating contracts/seed-fixtures.json against Section 5 & Section 8 of the V1 specification.
"""
from datetime import datetime
import pytest

pytestmark = pytest.mark.contract


def test_seed_fixtures_top_level(seed_fixtures):
    """Verifies that seed-fixtures.json contains both seed_data and mock_responses."""
    assert "seed_data" in seed_fixtures, "Missing seed_data in seed-fixtures.json"
    assert "mock_responses" in seed_fixtures, "Missing mock_responses in seed-fixtures.json"


def test_seed_class_contract(seed_fixtures):
    """Verifies the demo class structure conforms to requirements."""
    class_data = seed_fixtures["seed_data"]["class"]
    assert class_data["code"] == "LOP-DEMO"
    assert "id" in class_data
    assert "name" in class_data


def test_seed_users_and_roles(seed_fixtures):
    """Verifies the 6 demo users, roles, and class memberships."""
    users = seed_fixtures["seed_data"]["users"]
    user_map = {u["username"]: u for u in users}

    expected_users = {
        "sv001": "STUDENT",
        "sv002": "STUDENT",
        "sv003": "STUDENT",
        "bcs001": "BCS",
        "gvcn001": "GVCN",
        "admin001": "ADMIN",
    }

    assert len(users) == 6, "Must define exactly 6 demo users"
    for username, role in expected_users.items():
        assert username in user_map, f"Missing user {username}"
        assert user_map[username]["role"] == role, f"User {username} must have role {role}"
        assert "full_name" in user_map[username]
        assert "id" in user_map[username]

    class_id = seed_fixtures["seed_data"]["class"]["id"]
    for username in ["sv001", "sv002", "sv003", "bcs001", "gvcn001"]:
        assert user_map[username].get("class_id") == class_id, f"User {username} must belong to class {class_id}"
    assert user_map["admin001"].get("class_id") is None, "ADMIN must not be bound to a single class"


def test_seed_campaign_configuration(seed_fixtures):
    """Verifies campaign constraints defined in Section 5 (dates, reminder, rounds)."""
    campaign = seed_fixtures["seed_data"]["campaign"]

    assert campaign["status"] == "DRAFT", "Initial campaign in seed data must be in DRAFT"
    assert "term" in campaign and len(campaign["term"]) > 0

    open_at = datetime.fromisoformat(campaign["open_at"].replace("Z", "+00:00"))
    sub_deadline = datetime.fromisoformat(campaign["submission_deadline_at"].replace("Z", "+00:00"))
    assert open_at < sub_deadline, "open_at must be strictly before submission_deadline_at"

    reminder_hours = campaign["reminder_after_hours"]
    appeal_hours = campaign["appeal_period_hours"]
    assert 0 < reminder_hours < appeal_hours, "0 < reminder_after_hours < appeal_period_hours"

    assert campaign["max_info_rounds"] >= 0, "max_info_rounds must be >= 0"
    assert campaign["max_proof_rounds"] >= 0, "max_proof_rounds must be >= 0"


def test_seed_criteria_integrity(seed_fixtures):
    """Verifies demo criteria (TC01, TC02, TC03) conform to Section 8."""
    criteria = seed_fixtures["seed_data"]["campaign"]["criteria"]
    assert len(criteria) == 3, "Must define exactly 3 demo criteria"

    codes = [c["code"] for c in criteria]
    assert codes == ["TC01", "TC02", "TC03"]

    for c in criteria:
        assert float(c["max_score"]) > 0, "Criterion max_score must be positive"
        assert isinstance(c["requires_evidence"], bool), "requires_evidence must be boolean"
        assert isinstance(c["sort_order"], int), "sort_order must be an integer"


def test_mock_responses_presence_and_structure(seed_fixtures):
    """Verifies that all 7 required mock responses are present for frontend development."""
    mocks = seed_fixtures["mock_responses"]
    required_mocks = [
        "student_current_draft",
        "student_current_needs_info",
        "student_current_published",
        "bcs_overview",
        "bcs_case_detail",
        "bcs_scoreboard",
        "gvcn_final_scores",
    ]

    for mock_name in required_mocks:
        assert mock_name in mocks, f"Missing mock response: {mock_name}"

    # Verify confidentiality rule in draft mock
    draft_claims = mocks["student_current_draft"]["claims"]
    for cl in draft_claims:
        assert cl.get("approved_score") is None, "Before PUBLISHED, approved_score must be hidden from student"
        assert cl.get("bcs_reason") is None, "Before PUBLISHED, bcs_reason must be hidden from student"
    assert mocks["student_current_draft"]["case"].get("proposed_total") is None

    # Verify published mock reveals proposed_total and appeal deadline
    pub_case = mocks["student_current_published"]["case"]
    assert pub_case["status"] == "PUBLISHED"
    assert pub_case.get("proposed_total") is not None
    assert pub_case.get("appeal_deadline_at") is not None
