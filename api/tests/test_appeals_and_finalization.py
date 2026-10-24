import io
import pytest
from datetime import datetime, timezone
from api.tests.conftest import login_helper
from api.app.models.entities import AuditEvent


def _setup_published_campaign(client, seed_data):
    auth_sv1 = login_helper(client, "sv001")
    auth_sv2 = login_helper(client, "sv002")
    auth_sv3 = login_helper(client, "sv003")
    auth_bcs = login_helper(client, "bcs001")
    camp = seed_data["campaign"]
    criteria = seed_data["criteria"]
    cases = seed_data["cases"]

    for auth_sv, c in [(auth_sv1, cases[0]), (auth_sv2, cases[1]), (auth_sv3, cases[2])]:
        for crit in criteria:
            client.put(
                f"/api/v1/student/cases/{c.id}/claims/{crit.id}",
                json={"self_score": "8.00", "expected_version": c.version},
                cookies=auth_sv["cookies"],
                headers=auth_sv["headers"],
            )
            c.version += 1
            if crit.requires_evidence:
                pdf = io.BytesIO(b"%PDF evidence")
                client.post(
                    f"/api/v1/student/cases/{c.id}/evidence",
                    data={"criterion_id": crit.id},
                    files={"file": ("f.pdf", pdf, "application/pdf")},
                    cookies=auth_sv["cookies"],
                    headers=auth_sv["headers"],
                )

        resp_sub = client.post(f"/api/v1/student/cases/{c.id}/submit", json={"expected_version": c.version}, cookies=auth_sv["cookies"], headers=auth_sv["headers"])
        c.version = resp_sub.json()["version"]

        for crit in criteria:
            resp_rev = client.put(f"/api/v1/bcs/cases/{c.id}/claims/{crit.id}/review", json={"approved_score": "8.00", "reason": None, "expected_version": c.version}, cookies=auth_bcs["cookies"], headers=auth_bcs["headers"])
            c.version = resp_rev.json()["version"]

        resp_comp = client.post(f"/api/v1/bcs/cases/{c.id}/complete-review", json={"expected_version": c.version}, cookies=auth_bcs["cookies"], headers=auth_bcs["headers"])
        c.version = resp_comp.json()["version"]

    client.post(f"/api/v1/bcs/campaigns/{camp.id}/meetings", json={"kind": "BCS", "held_at": "2026-10-25T14:00:00Z"}, cookies=auth_bcs["cookies"], headers=auth_bcs["headers"])
    client.post(f"/api/v1/bcs/campaigns/{camp.id}/meetings", json={"kind": "CLASS", "held_at": "2026-10-26T14:00:00Z"}, cookies=auth_bcs["cookies"], headers=auth_bcs["headers"])
    client.post(f"/api/v1/bcs/campaigns/{camp.id}/publish", cookies=auth_bcs["cookies"], headers=auth_bcs["headers"])

    return {"auth_sv1": auth_sv1, "auth_sv2": auth_sv2, "auth_sv3": auth_sv3, "auth_bcs": auth_bcs}


def test_acceptance_criteria_11_appeals_resolution_keep_and_adjust(client, seed_data, db):
    """
    Tiêu chí 11: BCS giải quyết khiếu nại KEEP và ADJUST;
    điểm cũ/mới, lý do, người xử lý đều truy được.
    """
    auths = _setup_published_campaign(client, seed_data)
    auth_sv1 = auths["auth_sv1"]
    auth_bcs = auths["auth_bcs"]
    case0 = seed_data["cases"][0]
    crit1, crit2, _ = seed_data["criteria"]

    # sv001 submits appeals for TC01 and TC02
    cur = client.get("/api/v1/student/current", cookies=auth_sv1["cookies"]).json()
    resp_app = client.post(
        f"/api/v1/student/cases/{case0.id}/appeals",
        json={
            "expected_version": cur["case"]["version"],
            "items": [
                {"criterion_id": crit1.id, "reason": "Xin nâng điểm TC01"},
                {"criterion_id": crit2.id, "reason": "Xem lại điểm TC02"},
            ],
        },
        cookies=auth_sv1["cookies"],
        headers=auth_sv1["headers"],
    )
    assert resp_app.status_code == 200
    appeals_data = resp_app.json()["appeals"]
    app_tc1 = next(a for a in appeals_data if a["criterion_id"] == crit1.id)
    app_tc2 = next(a for a in appeals_data if a["criterion_id"] == crit2.id)

    # 1. BCS resolves TC01 with ADJUST: new_score = 10.00
    resp_res1 = client.post(
        f"/api/v1/bcs/appeals/{app_tc1['id']}/resolve",
        json={"resolution": "ADJUST", "new_score": "10.00", "reason": "BCS đồng ý tăng điểm do minh chứng hợp lệ"},
        cookies=auth_bcs["cookies"],
        headers=auth_bcs["headers"],
    )
    assert resp_res1.status_code == 200
    assert resp_res1.json()["status"] == "RESOLVED"
    assert resp_res1.json()["resolution"] == "ADJUST"
    assert resp_res1.json()["new_score"] == "10.00"

    # Case is still in APPEALED because TC02 appeal is still OPEN
    detail1 = client.get(f"/api/v1/bcs/cases/{case0.id}", cookies=auth_bcs["cookies"]).json()
    assert detail1["status"] == "APPEALED"

    # 2. BCS resolves TC02 with KEEP
    resp_res2 = client.post(
        f"/api/v1/bcs/appeals/{app_tc2['id']}/resolve",
        json={"resolution": "KEEP", "new_score": None, "reason": "Giữ nguyên vì không có bằng chứng mới"},
        cookies=auth_bcs["cookies"],
        headers=auth_bcs["headers"],
    )
    assert resp_res2.status_code == 200
    assert resp_res2.json()["status"] == "RESOLVED"
    assert resp_res2.json()["resolution"] == "KEEP"

    # Now all appeals are resolved -> Case status moves to RESOLVED
    detail2 = client.get(f"/api/v1/bcs/cases/{case0.id}", cookies=auth_bcs["cookies"]).json()
    assert detail2["status"] == "RESOLVED"
    # Proposed total was updated from 24.00 (8+8+8) to 26.00 (10+8+8)
    assert detail2["claims"][0]["approved_score"] == "10.00"

    # Check audit events for old and new scores
    audit = db.query(AuditEvent).filter(AuditEvent.action == "APPEAL_RESOLVED").all()
    assert len(audit) == 2


def test_acceptance_criteria_14_finalize_gate_and_gvcn_csv(client, seed_data):
    """
    Tiêu chí 14: Chỉ chốt khi mọi case đủ điều kiện; GVCN chỉ xem/tải CSV sau chốt.
    """
    auths = _setup_published_campaign(client, seed_data)
    auth_sv1 = auths["auth_sv1"]
    auth_sv2 = auths["auth_sv2"]
    auth_sv3 = auths["auth_sv3"]
    auth_bcs = auths["auth_bcs"]
    auth_gvcn = login_helper(client, "gvcn001")
    camp = seed_data["campaign"]
    cases = seed_data["cases"]

    # GVCN attempts download before FINALIZED -> 409 Conflict
    resp_gvcn_early = client.get(f"/api/v1/gvcn/campaigns/{camp.id}/final-scores.csv", cookies=auth_gvcn["cookies"])
    assert resp_gvcn_early.status_code == 409

    # BCS attempts finalize before all cases responded -> 422
    resp_fin_early = client.post(f"/api/v1/bcs/campaigns/{camp.id}/finalize", cookies=auth_bcs["cookies"], headers=auth_bcs["headers"])
    assert resp_fin_early.status_code == 422
    assert resp_fin_early.json()["error"]["code"] == "CASES_NOT_FINALIZABLE"

    # Students accept all cases
    for auth_sv, c in [(auth_sv1, cases[0]), (auth_sv2, cases[1]), (auth_sv3, cases[2])]:
        cur = client.get("/api/v1/student/current", cookies=auth_sv["cookies"]).json()
        client.post(f"/api/v1/student/cases/{c.id}/accept", json={"expected_version": cur["case"]["version"]}, cookies=auth_sv["cookies"], headers=auth_sv["headers"])

    # Now BCS finalizes campaign -> 200 OK
    resp_finalize = client.post(f"/api/v1/bcs/campaigns/{camp.id}/finalize", cookies=auth_bcs["cookies"], headers=auth_bcs["headers"])
    assert resp_finalize.status_code == 200
    assert resp_finalize.json()["status"] == "FINALIZED"

    # Now GVCN downloads final scores CSV -> 200 OK with CSV headers & content
    resp_gvcn_csv = client.get(f"/api/v1/gvcn/campaigns/{camp.id}/final-scores.csv", cookies=auth_gvcn["cookies"])
    assert resp_gvcn_csv.status_code == 200
    assert "text/csv" in resp_gvcn_csv.headers["content-type"]
    text = resp_gvcn_csv.text
    assert "Mã sinh viên" in text
    assert "sv001" in text
    assert "sv002" in text
    assert "sv003" in text
    assert "FINALIZED" in text
