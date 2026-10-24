import io
import pytest
from datetime import datetime, timezone
from api.tests.conftest import login_helper


def _setup_case_to_proposed(client, auth_sv, auth_bcs, case, criteria):
    for crit in criteria:
        client.put(
            f"/api/v1/student/cases/{case.id}/claims/{crit.id}",
            json={"self_score": "8.00", "expected_version": case.version},
            cookies=auth_sv["cookies"],
            headers=auth_sv["headers"],
        )
        case.version += 1
        if crit.requires_evidence:
            pdf = io.BytesIO(b"%PDF content")
            client.post(
                f"/api/v1/student/cases/{case.id}/evidence",
                data={"criterion_id": crit.id},
                files={"file": ("f.pdf", pdf, "application/pdf")},
                cookies=auth_sv["cookies"],
                headers=auth_sv["headers"],
            )

    resp_sub = client.post(
        f"/api/v1/student/cases/{case.id}/submit",
        json={"expected_version": case.version},
        cookies=auth_sv["cookies"],
        headers=auth_sv["headers"],
    )
    case.version = resp_sub.json()["version"]

    for crit in criteria:
        resp_rev = client.put(
            f"/api/v1/bcs/cases/{case.id}/claims/{crit.id}/review",
            json={"approved_score": "8.00", "reason": None, "expected_version": case.version},
            cookies=auth_bcs["cookies"],
            headers=auth_bcs["headers"],
        )
        case.version = resp_rev.json()["version"]

    resp_comp = client.post(
        f"/api/v1/bcs/cases/{case.id}/complete-review",
        json={"expected_version": case.version},
        cookies=auth_bcs["cookies"],
        headers=auth_bcs["headers"],
    )
    case.version = resp_comp.json()["version"]
    case.status = "PROPOSED"


def test_acceptance_criteria_8_meetings_and_publish_gate(client, seed_data):
    """
    Tiêu chí 8: Chưa đủ hai cuộc họp hoặc còn case chờ BCS thì không công bố;
    đủ điều kiện thì công bố một lần.
    """
    auth_sv1 = login_helper(client, "sv001")
    auth_sv2 = login_helper(client, "sv002")
    auth_sv3 = login_helper(client, "sv003")
    auth_bcs = login_helper(client, "bcs001")
    camp = seed_data["campaign"]
    criteria = seed_data["criteria"]
    cases = seed_data["cases"]

    # Only case 0 is moved to PROPOSED; case 1 and 2 are still in DRAFT
    _setup_case_to_proposed(client, auth_sv1, auth_bcs, cases[0], criteria)

    # 1. Try publish without meetings and with pending cases -> 422
    resp_pub1 = client.post(
        f"/api/v1/bcs/campaigns/{camp.id}/publish",
        json={"expected_campaign_status": "OPEN"},
        cookies=auth_bcs["cookies"],
        headers=auth_bcs["headers"],
    )
    assert resp_pub1.status_code == 422

    # Add only BCS meeting
    client.post(
        f"/api/v1/bcs/campaigns/{camp.id}/meetings",
        json={"kind": "BCS", "held_at": "2026-10-25T14:00:00Z", "note": "Họp BCS"},
        cookies=auth_bcs["cookies"],
        headers=auth_bcs["headers"],
    )

    # Still missing CLASS meeting -> 422
    resp_pub2 = client.post(
        f"/api/v1/bcs/campaigns/{camp.id}/publish",
        cookies=auth_bcs["cookies"],
        headers=auth_bcs["headers"],
    )
    assert resp_pub2.status_code == 422
    assert resp_pub2.json()["error"]["code"] == "MEETINGS_INCOMPLETE"

    # Add CLASS meeting
    client.post(
        f"/api/v1/bcs/campaigns/{camp.id}/meetings",
        json={"kind": "CLASS", "held_at": "2026-10-26T14:00:00Z", "note": "Họp Lớp"},
        cookies=auth_bcs["cookies"],
        headers=auth_bcs["headers"],
    )

    # Now meetings are complete, but cases 1 and 2 are still in DRAFT -> 422 CASES_NOT_READY
    resp_pub3 = client.post(
        f"/api/v1/bcs/campaigns/{camp.id}/publish",
        cookies=auth_bcs["cookies"],
        headers=auth_bcs["headers"],
    )
    assert resp_pub3.status_code == 422
    assert resp_pub3.json()["error"]["code"] == "CASES_NOT_READY"

    # Move case 1 and case 2 to PROPOSED as well
    _setup_case_to_proposed(client, auth_sv2, auth_bcs, cases[1], criteria)
    _setup_case_to_proposed(client, auth_sv3, auth_bcs, cases[2], criteria)

    # Now all cases are PROPOSED and both meetings exist -> Publish succeeds!
    resp_pub_success = client.post(
        f"/api/v1/bcs/campaigns/{camp.id}/publish",
        cookies=auth_bcs["cookies"],
        headers=auth_bcs["headers"],
    )
    assert resp_pub_success.status_code == 200
    assert resp_pub_success.json()["status"] == "PUBLISHED"


def test_acceptance_criteria_9_score_masking_before_and_after_publish(client, seed_data):
    """
    Tiêu chí 9: Trước công bố SV không thấy điểm dự kiến; sau công bố thấy đúng điểm và hạn phản hồi.
    """
    auth_sv1 = login_helper(client, "sv001")
    auth_sv2 = login_helper(client, "sv002")
    auth_sv3 = login_helper(client, "sv003")
    auth_bcs = login_helper(client, "bcs001")
    camp = seed_data["campaign"]
    criteria = seed_data["criteria"]
    cases = seed_data["cases"]

    _setup_case_to_proposed(client, auth_sv1, auth_bcs, cases[0], criteria)

    # Case 0 is now PROPOSED, but campaign is NOT yet PUBLISHED
    # SV1 checks GET /student/current: proposed_total and approved_score MUST be None!
    resp_pre = client.get("/api/v1/student/current", cookies=auth_sv1["cookies"])
    assert resp_pre.status_code == 200
    pre_data = resp_pre.json()
    assert pre_data["case"]["proposed_total"] is None
    for cl in pre_data["claims"]:
        assert cl["approved_score"] is None
        assert cl["bcs_reason"] is None

    # Setup other cases and meetings to publish
    _setup_case_to_proposed(client, auth_sv2, auth_bcs, cases[1], criteria)
    _setup_case_to_proposed(client, auth_sv3, auth_bcs, cases[2], criteria)
    client.post(f"/api/v1/bcs/campaigns/{camp.id}/meetings", json={"kind": "BCS", "held_at": "2026-10-25T14:00:00Z"}, cookies=auth_bcs["cookies"], headers=auth_bcs["headers"])
    client.post(f"/api/v1/bcs/campaigns/{camp.id}/meetings", json={"kind": "CLASS", "held_at": "2026-10-26T14:00:00Z"}, cookies=auth_bcs["cookies"], headers=auth_bcs["headers"])
    client.post(f"/api/v1/bcs/campaigns/{camp.id}/publish", cookies=auth_bcs["cookies"], headers=auth_bcs["headers"])

    # Now campaign is PUBLISHED. SV1 checks GET /student/current again
    resp_post = client.get("/api/v1/student/current", cookies=auth_sv1["cookies"])
    assert resp_post.status_code == 200
    post_data = resp_post.json()
    assert post_data["case"]["status"] == "PUBLISHED"
    assert post_data["case"]["proposed_total"] == "24.00"
    assert post_data["case"]["appeal_deadline_at"] is not None
    for cl in post_data["claims"]:
        assert cl["approved_score"] == "8.00"


def test_acceptance_criteria_10_accept_appeal_mutual_exclusion(client, seed_data):
    """
    Tiêu chí 10: SV đồng ý thì không thể khiếu nại; khiếu nại thì không thể đồng ý.
    """
    auth_sv1 = login_helper(client, "sv001")
    auth_sv2 = login_helper(client, "sv002")
    auth_sv3 = login_helper(client, "sv003")
    auth_bcs = login_helper(client, "bcs001")
    camp = seed_data["campaign"]
    criteria = seed_data["criteria"]
    cases = seed_data["cases"]

    _setup_case_to_proposed(client, auth_sv1, auth_bcs, cases[0], criteria)
    _setup_case_to_proposed(client, auth_sv2, auth_bcs, cases[1], criteria)
    _setup_case_to_proposed(client, auth_sv3, auth_bcs, cases[2], criteria)
    client.post(f"/api/v1/bcs/campaigns/{camp.id}/meetings", json={"kind": "BCS", "held_at": "2026-10-25T14:00:00Z"}, cookies=auth_bcs["cookies"], headers=auth_bcs["headers"])
    client.post(f"/api/v1/bcs/campaigns/{camp.id}/meetings", json={"kind": "CLASS", "held_at": "2026-10-26T14:00:00Z"}, cookies=auth_bcs["cookies"], headers=auth_bcs["headers"])
    client.post(f"/api/v1/bcs/campaigns/{camp.id}/publish", cookies=auth_bcs["cookies"], headers=auth_bcs["headers"])

    # Case 0 (sv001): SV accepts
    cur1 = client.get("/api/v1/student/current", cookies=auth_sv1["cookies"]).json()
    resp_accept = client.post(
        f"/api/v1/student/cases/{cases[0].id}/accept",
        json={"expected_version": cur1["case"]["version"]},
        cookies=auth_sv1["cookies"],
        headers=auth_sv1["headers"],
    )
    assert resp_accept.status_code == 200
    assert resp_accept.json()["status"] == "ACCEPTED"
    v_acc = resp_accept.json()["version"]

    # sv001 now tries to submit appeals -> 409 Conflict
    resp_app_after_acc = client.post(
        f"/api/v1/student/cases/{cases[0].id}/appeals",
        json={"expected_version": v_acc, "items": [{"criterion_id": criteria[0].id, "reason": "Khiếu nại sau đồng ý"}]},
        cookies=auth_sv1["cookies"],
        headers=auth_sv1["headers"],
    )
    assert resp_app_after_acc.status_code == 409

    # Case 1 (sv002): SV appeals
    cur2 = client.get("/api/v1/student/current", cookies=auth_sv2["cookies"]).json()
    resp_appeal = client.post(
        f"/api/v1/student/cases/{cases[1].id}/appeals",
        json={"expected_version": cur2["case"]["version"], "items": [{"criterion_id": criteria[0].id, "reason": "Đề nghị xem lại TC01"}]},
        cookies=auth_sv2["cookies"],
        headers=auth_sv2["headers"],
    )
    assert resp_appeal.status_code == 200
    assert resp_appeal.json()["status"] == "APPEALED"
    v_app = resp_appeal.json()["version"]

    # sv002 now tries to accept -> 409 Conflict
    resp_acc_after_app = client.post(
        f"/api/v1/student/cases/{cases[1].id}/accept",
        json={"expected_version": v_app},
        cookies=auth_sv2["cookies"],
        headers=auth_sv2["headers"],
    )
    assert resp_acc_after_app.status_code == 409
