import io
import pytest
from api.tests.conftest import login_helper


def test_acceptance_criteria_3_save_draft_and_total(client, seed_data):
    """
    Tiêu chí 3: Form lưu nháp rồi tải lại giữ nguyên điểm và tệp; tổng tự khai đúng.
    """
    auth = login_helper(client, "sv001")
    case = seed_data["cases"][0]
    crit1, crit2, crit3 = seed_data["criteria"]

    # 1. Update self_score for TC01 (8.00)
    resp1 = client.put(
        f"/api/v1/student/cases/{case.id}/claims/{crit1.id}",
        json={"self_score": "8.00", "student_note": "Ghi chú TC01", "expected_version": 1},
        cookies=auth["cookies"],
        headers=auth["headers"],
    )
    assert resp1.status_code == 200
    assert resp1.json()["claim"]["self_score"] == "8.00"
    assert resp1.json()["version"] == 2

    # 2. Update self_score for TC02 (7.50)
    resp2 = client.put(
        f"/api/v1/student/cases/{case.id}/claims/{crit2.id}",
        json={"self_score": "7.50", "student_note": "Ghi chú TC02", "expected_version": 2},
        cookies=auth["cookies"],
        headers=auth["headers"],
    )
    assert resp2.status_code == 200
    assert resp2.json()["version"] == 3

    # 3. Reload student current
    resp_cur = client.get("/api/v1/student/current", cookies=auth["cookies"])
    assert resp_cur.status_code == 200
    data = resp_cur.json()
    assert data["case"]["claimed_total"] == "15.50"
    assert data["case"]["status"] == "DRAFT"
    assert data["case"]["version"] == 3


def test_acceptance_criteria_15_file_upload_security(client, seed_data):
    """
    Tiêu chí 15: Tệp không thể xem bằng URL storage trực tiếp;
    API kiểm quyền và MIME, chặn loại tệp ngoài PDF/JPG/PNG.
    """
    auth_sv1 = login_helper(client, "sv001")
    auth_sv2 = login_helper(client, "sv002")
    auth_bcs = login_helper(client, "bcs001")
    auth_gvcn = login_helper(client, "gvcn001")
    case = seed_data["cases"][0]
    crit1 = seed_data["criteria"][0]

    # Upload invalid file type (.exe / text/plain)
    fake_exe = io.BytesIO(b"executable content")
    resp_bad_mime = client.post(
        f"/api/v1/student/cases/{case.id}/evidence",
        data={"criterion_id": crit1.id},
        files={"file": ("virus.exe", fake_exe, "application/x-msdownload")},
        cookies=auth_sv1["cookies"],
        headers=auth_sv1["headers"],
    )
    assert resp_bad_mime.status_code == 422
    assert resp_bad_mime.json()["error"]["code"] == "INVALID_FILE_TYPE"

    # Upload valid PDF
    pdf_bytes = io.BytesIO(b"%PDF-1.4 sample pdf content")
    resp_upload = client.post(
        f"/api/v1/student/cases/{case.id}/evidence",
        data={"criterion_id": crit1.id},
        files={"file": ("chung-chi.pdf", pdf_bytes, "application/pdf")},
        cookies=auth_sv1["cookies"],
        headers=auth_sv1["headers"],
    )
    assert resp_upload.status_code == 201
    file_id = resp_upload.json()["id"]

    # 1. sv001 (owner) can download
    resp_owner_dl = client.get(f"/api/v1/files/{file_id}", cookies=auth_sv1["cookies"])
    assert resp_owner_dl.status_code == 200
    assert resp_owner_dl.content == b"%PDF-1.4 sample pdf content"

    # 2. bcs001 (class BCS) can download
    resp_bcs_dl = client.get(f"/api/v1/files/{file_id}", cookies=auth_bcs["cookies"])
    assert resp_bcs_dl.status_code == 200

    # 3. sv002 (another student) receives 403 Forbidden
    resp_sv2_dl = client.get(f"/api/v1/files/{file_id}", cookies=auth_sv2["cookies"])
    assert resp_sv2_dl.status_code == 403

    # 4. gvcn001 (GVCN) receives 403 Forbidden per V1 spec
    resp_gvcn_dl = client.get(f"/api/v1/files/{file_id}", cookies=auth_gvcn["cookies"])
    assert resp_gvcn_dl.status_code == 403


def test_acceptance_criteria_4_submit_missing_evidence_creates_needs_info(client, seed_data):
    """
    Tiêu chí 4: Nộp thiếu minh chứng bắt buộc tạo NEEDS_INFO và thông báo đúng mục;
    bổ sung đúng hạn quay lại BCS_REVIEW.
    """
    auth = login_helper(client, "sv001")
    case = seed_data["cases"][0]
    crit1, crit2, crit3 = seed_data["criteria"]
    # TC01 and TC03 require evidence. TC02 does not.

    # Fill all self_scores
    client.put(f"/api/v1/student/cases/{case.id}/claims/{crit1.id}", json={"self_score": "8.00", "expected_version": 1}, cookies=auth["cookies"], headers=auth["headers"])
    client.put(f"/api/v1/student/cases/{case.id}/claims/{crit2.id}", json={"self_score": "8.00", "expected_version": 2}, cookies=auth["cookies"], headers=auth["headers"])
    client.put(f"/api/v1/student/cases/{case.id}/claims/{crit3.id}", json={"self_score": "8.00", "expected_version": 3}, cookies=auth["cookies"], headers=auth["headers"])

    # Submit without uploading evidence for TC01 or TC03
    resp_sub = client.post(
        f"/api/v1/student/cases/{case.id}/submit",
        json={"expected_version": 4},
        cookies=auth["cookies"],
        headers=auth["headers"],
    )
    assert resp_sub.status_code == 200
    data = resp_sub.json()
    assert data["status"] == "NEEDS_INFO"
    assert len(data["missing_items"]) == 2  # TC01 and TC03
    ver = data["version"]

    # Check notification sent
    resp_notif = client.get("/api/v1/notifications", cookies=auth["cookies"])
    assert resp_notif.status_code == 200
    notifs = resp_notif.json()
    assert any(n["type"] == "NEEDS_INFO" for n in notifs)

    # Now fulfill missing evidence
    pdf1 = io.BytesIO(b"%PDF evidence for TC01")
    client.post(f"/api/v1/student/cases/{case.id}/evidence", data={"criterion_id": crit1.id}, files={"file": ("tc01.pdf", pdf1, "application/pdf")}, cookies=auth["cookies"], headers=auth["headers"])

    pdf3 = io.BytesIO(b"%PDF evidence for TC03")
    client.post(f"/api/v1/student/cases/{case.id}/evidence", data={"criterion_id": crit3.id}, files={"file": ("tc03.pdf", pdf3, "application/pdf")}, cookies=auth["cookies"], headers=auth["headers"])

    # Resubmit
    resp_resub = client.post(
        f"/api/v1/student/cases/{case.id}/submit",
        json={"expected_version": ver},
        cookies=auth["cookies"],
        headers=auth["headers"],
    )
    assert resp_resub.status_code == 200
    assert resp_resub.json()["status"] == "BCS_REVIEW"
    assert resp_resub.json()["missing_items"] == []


def test_acceptance_criteria_5_exceeding_info_rounds_closes_incomplete(client, seed_data):
    """
    Tiêu chí 5: Hết lượt hoặc hết hạn bổ sung INFO đóng CLOSED_INCOMPLETE; không tạo vòng lặp tiếp.
    """
    auth = login_helper(client, "sv002")
    case = seed_data["cases"][1]
    crit1, crit2, crit3 = seed_data["criteria"]

    # Fill self scores
    client.put(f"/api/v1/student/cases/{case.id}/claims/{crit1.id}", json={"self_score": "8.00", "expected_version": 1}, cookies=auth["cookies"], headers=auth["headers"])
    client.put(f"/api/v1/student/cases/{case.id}/claims/{crit2.id}", json={"self_score": "8.00", "expected_version": 2}, cookies=auth["cookies"], headers=auth["headers"])
    client.put(f"/api/v1/student/cases/{case.id}/claims/{crit3.id}", json={"self_score": "8.00", "expected_version": 3}, cookies=auth["cookies"], headers=auth["headers"])

    # Submit round 1 (missing evidence) -> NEEDS_INFO (round 1)
    resp1 = client.post(f"/api/v1/student/cases/{case.id}/submit", json={"expected_version": 4}, cookies=auth["cookies"], headers=auth["headers"])
    assert resp1.json()["status"] == "NEEDS_INFO"
    v1 = resp1.json()["version"]

    # Resubmit without uploading -> NEEDS_INFO (round 2, reaching max_info_rounds=2)
    resp2 = client.post(f"/api/v1/student/cases/{case.id}/submit", json={"expected_version": v1}, cookies=auth["cookies"], headers=auth["headers"])
    assert resp2.json()["status"] == "NEEDS_INFO"
    v2 = resp2.json()["version"]

    # Resubmit third time (exceeding max_info_rounds=2) -> CLOSED_INCOMPLETE
    resp3 = client.post(f"/api/v1/student/cases/{case.id}/submit", json={"expected_version": v2}, cookies=auth["cookies"], headers=auth["headers"])
    assert resp3.json()["status"] == "CLOSED_INCOMPLETE"

    # Cannot resubmit when CLOSED_INCOMPLETE
    v3 = resp3.json()["version"]
    resp4 = client.post(f"/api/v1/student/cases/{case.id}/submit", json={"expected_version": v3}, cookies=auth["cookies"], headers=auth["headers"])
    assert resp4.status_code == 409
    assert resp4.json()["error"]["code"] == "INVALID_STATE"
