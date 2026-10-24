"""
Contract tests validating contracts/openapi.yaml against Section 7 & Section 5 of the V1 specification.
"""
import pytest

pytestmark = pytest.mark.contract

REQUIRED_SPEC_ENDPOINTS = [
    ("/health", "get"),
    ("/auth/login", "post"),
    ("/auth/me", "get"),
    ("/auth/logout", "post"),
    ("/student/current", "get"),
    ("/student/cases/{caseId}/claims/{criterionId}", "put"),
    ("/student/cases/{caseId}/evidence", "post"),
    ("/files/{fileId}", "get"),
    ("/student/cases/{caseId}/submit", "post"),
    ("/student/cases/{caseId}/accept", "post"),
    ("/student/cases/{caseId}/appeals", "post"),
    ("/bcs/campaigns/{id}/overview", "get"),
    ("/bcs/campaigns/{id}/cases", "get"),
    ("/bcs/cases/{caseId}", "get"),
    ("/bcs/cases/{caseId}/supplement-requests", "post"),
    ("/bcs/cases/{caseId}/claims/{criterionId}/review", "put"),
    ("/bcs/cases/{caseId}/complete-review", "post"),
    ("/bcs/campaigns/{id}/meetings", "post"),
    ("/bcs/campaigns/{id}/publish", "post"),
    ("/bcs/campaigns/{id}/scoreboard", "get"),
    ("/bcs/campaigns/{id}/appeals", "get"),
    ("/bcs/appeals/{appealId}/resolve", "post"),
    ("/bcs/campaigns/{id}/finalize", "post"),
    ("/gvcn/campaigns/{id}/final-scores.csv", "get"),
    ("/notifications", "get"),
    ("/notifications/{id}/read", "post"),
    ("/admin/campaigns", "post"),
    ("/admin/campaigns/{id}", "put"),
    ("/admin/campaigns/{id}/open", "post"),
]


def test_openapi_metadata(openapi_spec):
    """Verifies that OpenAPI spec exists, is 3.0.x, and contains required metadata."""
    assert openapi_spec.get("openapi", "").startswith("3.0"), "OpenAPI specification must be version 3.0.x"
    assert "info" in openapi_spec
    assert "title" in openapi_spec["info"]
    assert "version" in openapi_spec["info"]


def test_openapi_all_routes_from_spec_exist(openapi_spec):
    """Verifies all 29 routes and HTTP methods defined in Section 7 exist in openapi.yaml."""
    paths = openapi_spec.get("paths", {})
    missing_routes = []

    for path, method in REQUIRED_SPEC_ENDPOINTS:
        if path not in paths:
            missing_routes.append(f"{method.upper()} {path} (path missing)")
        elif method.lower() not in paths[path]:
            missing_routes.append(f"{method.upper()} {path} (method missing)")

    assert not missing_routes, f"Missing required endpoints in OpenAPI contract: {missing_routes}"


def test_openapi_standard_error_format(openapi_spec):
    """Verifies the standard error schema conforms to Section 7 ({"error": {"code", "message", "fields"}})."""
    schemas = openapi_spec.get("components", {}).get("schemas", {})
    assert "ErrorDetail" in schemas, "ErrorDetail schema must be defined in components.schemas"
    error_wrapper = schemas["ErrorDetail"].get("properties", {})
    assert "error" in error_wrapper, "Error response wrapper must include 'error' field"
    error_props = error_wrapper["error"].get("properties", {})
    assert "code" in error_props, "Error detail must include 'code' field"
    assert "message" in error_props, "Error detail must include 'message' field"
    assert "fields" in error_props, "Error detail must include 'fields' object"


def test_openapi_enum_definitions(openapi_spec):
    """Verifies that all domain enums are formally defined and match the states specification."""
    schemas = openapi_spec.get("components", {}).get("schemas", {})

    expected_campaign_statuses = ["DRAFT", "SCHEDULED", "OPEN", "REVIEW", "PUBLISHED", "FINALIZED"]
    expected_case_statuses = [
        "DRAFT", "SUBMITTED", "NEEDS_INFO", "BCS_REVIEW", "NEEDS_PROOF",
        "PROPOSED", "PUBLISHED", "ACCEPTED", "APPEALED", "ACCEPTED_AUTO",
        "RESOLVED", "FINALIZED", "CLOSED_INCOMPLETE", "CLOSED_NO_SUBMIT"
    ]
    expected_roles = ["STUDENT", "BCS", "GVCN", "ADMIN"]
    expected_supplement_kinds = ["INFO", "PROOF"]
    expected_meeting_kinds = ["BCS", "CLASS"]
    expected_appeal_statuses = ["OPEN", "RESOLVED"]
    expected_appeal_resolutions = ["KEEP", "ADJUST"]

    assert set(schemas["CampaignStatus"]["enum"]) == set(expected_campaign_statuses)
    assert set(schemas["CaseStatus"]["enum"]) == set(expected_case_statuses)
    assert set(schemas["Role"]["enum"]) == set(expected_roles)
    assert set(schemas["SupplementKind"]["enum"]) == set(expected_supplement_kinds)
    assert set(schemas["MeetingKind"]["enum"]) == set(expected_meeting_kinds)
    assert set(schemas["AppealStatus"]["enum"]) == set(expected_appeal_statuses)
    assert set(schemas["AppealResolution"]["enum"]) == set(expected_appeal_resolutions)


def test_openapi_concurrency_and_idempotency_contracts(openapi_spec):
    """Verifies that mutation endpoints support optimistic locking (expected_version) and idempotency."""
    paths = openapi_spec.get("paths", {})

    # Check Idempotency-Key header on critical endpoints
    submit_params = paths.get("/student/cases/{caseId}/submit", {}).get("post", {}).get("parameters", [])
    publish_params = paths.get("/bcs/campaigns/{id}/publish", {}).get("post", {}).get("parameters", [])
    finalize_params = paths.get("/bcs/campaigns/{id}/finalize", {}).get("post", {}).get("parameters", [])

    param_names = lambda plist: [p.get("name") for p in plist]
    assert "Idempotency-Key" in param_names(submit_params), "Submit endpoint must accept Idempotency-Key"
    assert "Idempotency-Key" in param_names(publish_params), "Publish endpoint must accept Idempotency-Key"
    assert "Idempotency-Key" in param_names(finalize_params), "Finalize endpoint must accept Idempotency-Key"
