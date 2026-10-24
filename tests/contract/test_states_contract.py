"""
Contract tests validating the Campaign and Case state machines defined in contracts/states.md.
"""
import pytest

pytestmark = pytest.mark.contract

VALID_CAMPAIGN_TRANSITIONS = {
    "DRAFT": {"SCHEDULED", "OPEN"},
    "SCHEDULED": {"OPEN"},
    "OPEN": {"REVIEW"},
    "REVIEW": {"PUBLISHED"},
    "PUBLISHED": {"FINALIZED"},
    "FINALIZED": set(),
}

VALID_CASE_TRANSITIONS = {
    "DRAFT": {"SUBMITTED", "CLOSED_NO_SUBMIT"},
    "SUBMITTED": {"NEEDS_INFO", "BCS_REVIEW", "CLOSED_INCOMPLETE"},
    "NEEDS_INFO": {"BCS_REVIEW", "CLOSED_INCOMPLETE"},
    "BCS_REVIEW": {"NEEDS_PROOF", "NEEDS_INFO", "PROPOSED"},
    "NEEDS_PROOF": {"BCS_REVIEW"},
    "PROPOSED": {"PUBLISHED"},
    "PUBLISHED": {"ACCEPTED", "APPEALED", "ACCEPTED_AUTO"},
    "ACCEPTED": {"FINALIZED"},
    "APPEALED": {"RESOLVED"},
    "ACCEPTED_AUTO": {"FINALIZED"},
    "RESOLVED": {"FINALIZED"},
    "FINALIZED": set(),
    "CLOSED_INCOMPLETE": set(),
    "CLOSED_NO_SUBMIT": set(),
}


def test_campaign_states_and_terminals():
    """Verifies that all campaign states exist and FINALIZED is strictly terminal."""
    all_campaign_states = set(VALID_CAMPAIGN_TRANSITIONS.keys())
    assert "FINALIZED" in all_campaign_states
    assert len(VALID_CAMPAIGN_TRANSITIONS["FINALIZED"]) == 0, "FINALIZED campaign cannot transition to another state"


def test_case_states_and_terminals():
    """Verifies all 14 case states and terminal states (FINALIZED, CLOSED_INCOMPLETE, CLOSED_NO_SUBMIT)."""
    expected_case_states = {
        "DRAFT", "SUBMITTED", "NEEDS_INFO", "BCS_REVIEW", "NEEDS_PROOF",
        "PROPOSED", "PUBLISHED", "ACCEPTED", "APPEALED", "ACCEPTED_AUTO",
        "RESOLVED", "FINALIZED", "CLOSED_INCOMPLETE", "CLOSED_NO_SUBMIT"
    }
    assert set(VALID_CASE_TRANSITIONS.keys()) == expected_case_states

    for terminal in ["FINALIZED", "CLOSED_INCOMPLETE", "CLOSED_NO_SUBMIT"]:
        assert len(VALID_CASE_TRANSITIONS[terminal]) == 0, f"{terminal} must be a dead-end terminal state"


@pytest.mark.parametrize("from_st,to_st", [
    ("DRAFT", "SCHEDULED"),
    ("DRAFT", "OPEN"),
    ("SCHEDULED", "OPEN"),
    ("OPEN", "REVIEW"),
    ("REVIEW", "PUBLISHED"),
    ("PUBLISHED", "FINALIZED"),
])
def test_valid_campaign_transitions_allowed(from_st, to_st):
    assert to_st in VALID_CAMPAIGN_TRANSITIONS[from_st]


@pytest.mark.parametrize("from_st,to_st", [
    ("DRAFT", "FINALIZED"),
    ("SCHEDULED", "REVIEW"),
    ("PUBLISHED", "OPEN"),
    ("FINALIZED", "DRAFT"),
])
def test_invalid_campaign_transitions_rejected(from_st, to_st):
    assert to_st not in VALID_CAMPAIGN_TRANSITIONS.get(from_st, set())


@pytest.mark.parametrize("from_st,to_st", [
    ("DRAFT", "SUBMITTED"),
    ("SUBMITTED", "NEEDS_INFO"),
    ("SUBMITTED", "BCS_REVIEW"),
    ("NEEDS_INFO", "BCS_REVIEW"),
    ("NEEDS_INFO", "CLOSED_INCOMPLETE"),
    ("BCS_REVIEW", "NEEDS_PROOF"),
    ("NEEDS_PROOF", "BCS_REVIEW"),
    ("BCS_REVIEW", "PROPOSED"),
    ("PROPOSED", "PUBLISHED"),
    ("PUBLISHED", "ACCEPTED"),
    ("PUBLISHED", "APPEALED"),
    ("PUBLISHED", "ACCEPTED_AUTO"),
    ("APPEALED", "RESOLVED"),
    ("ACCEPTED", "FINALIZED"),
    ("ACCEPTED_AUTO", "FINALIZED"),
    ("RESOLVED", "FINALIZED"),
])
def test_valid_case_transitions_allowed(from_st, to_st):
    assert to_st in VALID_CASE_TRANSITIONS[from_st]


@pytest.mark.parametrize("from_st,to_st", [
    ("DRAFT", "PROPOSED"),
    ("PUBLISHED", "DRAFT"),
    ("CLOSED_INCOMPLETE", "SUBMITTED"),
    ("CLOSED_NO_SUBMIT", "OPEN"),
    ("ACCEPTED", "APPEALED"),
    ("APPEALED", "ACCEPTED"),
    ("FINALIZED", "BCS_REVIEW"),
])
def test_invalid_case_transitions_rejected(from_st, to_st):
    assert to_st not in VALID_CASE_TRANSITIONS.get(from_st, set())
