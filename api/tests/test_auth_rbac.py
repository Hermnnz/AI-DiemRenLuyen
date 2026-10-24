import pytest
from api.tests.conftest import login_helper


def test_login_success_and_cookie(client, seed_data):
    resp = client.post("/api/v1/auth/login", json={"username": "sv001", "password": "Demo@123456"})
    assert resp.status_code == 200
    data = resp.json()
    assert "user" in data
    assert data["user"]["username"] == "sv001"
    assert data["user"]["role"] == "STUDENT"
    assert "c1111111-1111-1111-1111-111111111111" in data["user"]["class_ids"]
    assert "csrf_token" in data
    assert "session_id" in resp.cookies


def test_login_invalid_password(client, seed_data):
    resp = client.post("/api/v1/auth/login", json={"username": "sv001", "password": "WrongPassword"})
    assert resp.status_code == 401
    data = resp.json()
    assert data["error"]["code"] == "UNAUTHORIZED"


def test_get_me_flow(client, seed_data):
    # Unauthenticated
    resp_unauth = client.get("/api/v1/auth/me")
    assert resp_unauth.status_code == 401

    # Authenticated
    auth = login_helper(client, "sv001")
    resp_auth = client.get("/api/v1/auth/me", cookies=auth["cookies"])
    assert resp_auth.status_code == 200
    data = resp_auth.json()
    assert data["user"]["username"] == "sv001"
    assert data["csrf_token"] == auth["headers"]["X-CSRF-Token"]


def test_logout_flow(client, seed_data):
    auth = login_helper(client, "sv001")
    resp_logout = client.post("/api/v1/auth/logout", cookies=auth["cookies"])
    assert resp_logout.status_code == 200

    # Next call to /auth/me should fail with 401
    resp_me = client.get("/api/v1/auth/me", cookies=auth["cookies"])
    assert resp_me.status_code == 401


def test_csrf_protection_on_mutations(client, seed_data):
    auth = login_helper(client, "sv001")
    case_id = seed_data["cases"][0].id
    crit_id = seed_data["criteria"][0].id

    # Call PUT without X-CSRF-Token header -> 403 FORBIDDEN
    resp_no_csrf = client.put(
        f"/api/v1/student/cases/{case_id}/claims/{crit_id}",
        json={"self_score": "8.00", "expected_version": 1},
        cookies=auth["cookies"],
    )
    assert resp_no_csrf.status_code == 403
    assert resp_no_csrf.json()["error"]["code"] == "FORBIDDEN"

    # Call PUT with invalid X-CSRF-Token -> 403 FORBIDDEN
    resp_bad_csrf = client.put(
        f"/api/v1/student/cases/{case_id}/claims/{crit_id}",
        json={"self_score": "8.00", "expected_version": 1},
        cookies=auth["cookies"],
        headers={"X-CSRF-Token": "invalid_fake_token"},
    )
    assert resp_bad_csrf.status_code == 403

    # Call PUT with valid X-CSRF-Token -> 200 OK
    resp_valid = client.put(
        f"/api/v1/student/cases/{case_id}/claims/{crit_id}",
        json={"self_score": "8.00", "expected_version": 1},
        cookies=auth["cookies"],
        headers=auth["headers"],
    )
    assert resp_valid.status_code == 200


def test_acceptance_criteria_1_student_isolation(client, seed_data):
    """
    Tiêu chí 1: STUDENT chỉ thấy case của chính mình;
    sửa ID trên URL/API để đọc/sửa case khác nhận 404/403.
    """
    auth_sv1 = login_helper(client, "sv001")
    case_sv2 = seed_data["cases"][1]  # Belongs to sv002
    crit_id = seed_data["criteria"][0].id

    # sv001 tries to edit sv002's claim
    resp = client.put(
        f"/api/v1/student/cases/{case_sv2.id}/claims/{crit_id}",
        json={"self_score": "9.00", "expected_version": 1},
        cookies=auth_sv1["cookies"],
        headers=auth_sv1["headers"],
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"

    # sv001 tries to submit sv002's case
    resp_sub = client.post(
        f"/api/v1/student/cases/{case_sv2.id}/submit",
        json={"expected_version": 1},
        cookies=auth_sv1["cookies"],
        headers=auth_sv1["headers"],
    )
    assert resp_sub.status_code == 403


def test_acceptance_criteria_2_bcs_cross_class_and_gvcn_rbac(client, seed_data):
    """
    Tiêu chí 2: BCS lớp A không mở được case lớp B; GVCN không gọi API sửa điểm.
    """
    auth_bcs_other = login_helper(client, "bcs_other")  # BCS of Class B
    camp_demo = seed_data["campaign"]  # Campaign of Class A
    case_sv1 = seed_data["cases"][0]   # Case of Class A
    crit_id = seed_data["criteria"][0].id

    # BCS other tries to access overview of Class A's campaign
    resp_ov = client.get(
        f"/api/v1/bcs/campaigns/{camp_demo.id}/overview",
        cookies=auth_bcs_other["cookies"],
    )
    assert resp_ov.status_code == 403
    assert resp_ov.json()["error"]["code"] == "FORBIDDEN"

    # BCS other tries to view detail of Class A's case
    resp_detail = client.get(
        f"/api/v1/bcs/cases/{case_sv1.id}",
        cookies=auth_bcs_other["cookies"],
    )
    assert resp_detail.status_code == 403

    # GVCN tries to review/modify scores (endpoint only for BCS)
    auth_gvcn = login_helper(client, "gvcn001")
    resp_gvcn_edit = client.put(
        f"/api/v1/bcs/cases/{case_sv1.id}/claims/{crit_id}/review",
        json={"approved_score": "8.00", "reason": "GVCN thử chấm", "expected_version": 1},
        cookies=auth_gvcn["cookies"],
        headers=auth_gvcn["headers"],
    )
    assert resp_gvcn_edit.status_code == 403
    assert resp_gvcn_edit.json()["error"]["code"] == "FORBIDDEN"
