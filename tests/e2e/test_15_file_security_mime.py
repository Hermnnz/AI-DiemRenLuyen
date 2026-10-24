"""
Acceptance Test 15 - Section 9.15:
Tệp không thể xem bằng URL storage trực tiếp; API kiểm quyền và MIME, chặn loại tệp ngoài PDF/JPG/PNG.
"""
import io
import os
import pytest
from tests.fixtures.client import AcceptanceTestClient

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.skipif(
        not os.getenv("RUN_ACCEPTANCE_TESTS"),
        reason="Chờ ghép backend/UI ở Giai đoạn 2 (Backend routes hiện là shell từ foundation-v1)"
    )
]


def test_15_file_upload_mime_validation_and_access_security(api_client: AcceptanceTestClient):
    """
    Kịch bản:
    1. Sinh viên upload loại tệp bị cấm (.exe, .sh, .docx, .html) -> API trả về 422 Unprocessable Entity.
    2. Sinh viên upload tệp hợp lệ (PDF, JPG, PNG) -> API trả về 200 kèm metadata, KHÔNG để lộ đường dẫn storage nội bộ.
    3. Kiểm tra bảo mật truy cập tệp GET /files/{fileId}:
       - Người dùng chưa đăng nhập -> 401 Unauthorized.
       - Sinh viên khác (sv002) cố xem tệp của sv001 -> 403 Forbidden.
       - GVCN thử truy cập xem tệp minh chứng (V1 quy định GVCN chỉ xem bảng điểm) -> 403 Forbidden.
       - Chính chủ sinh viên (sv001) hoặc BCS phụ trách lớp (bcs001) -> 200 OK stream tệp.
    """
    api_client.login_as_student("sv001")
    current_data = api_client.get("/api/v1/student/current").json()
    case_id = current_data["case"]["id"]
    tc01_id = current_data["criteria"][0]["id"]

    # 1. Reject disallowed file type (e.g., .exe / script)
    bad_file = {"file": ("malicious.exe", io.BytesIO(b"MZ executable header"), "application/octet-stream")}
    res_bad = api_client.post(
        f"/api/v1/student/cases/{case_id}/evidence",
        data={"criterion_id": tc01_id},
        files=bad_file
    )
    assert res_bad.status_code == 422, "Disallowed file type must be rejected with 422"

    # 2. Accept allowed file type (PDF)
    good_pdf = {"file": ("chung_chi.pdf", io.BytesIO(b"%PDF-1.4 sample evidence binary"), "application/pdf")}
    res_good = api_client.post(
        f"/api/v1/student/cases/{case_id}/evidence",
        data={"criterion_id": tc01_id},
        files=good_pdf
    )
    assert res_good.status_code in [200, 201]
    file_meta = res_good.json()
    file_id = file_meta.get("id")
    assert file_id is not None
    assert "storage_key" not in file_meta, "Internal storage_key must not be exposed to client"

    # 3. Access control on GET /files/{fileId}
    # Anonymous request
    anon_client = AcceptanceTestClient()
    res_anon = anon_client.get(f"/api/v1/files/{file_id}")
    assert res_anon.status_code == 401, "Unauthenticated access must return 401"

    # Another student request
    api_client.logout()
    api_client.login_as_student("sv002")
    res_sv2 = api_client.get(f"/api/v1/files/{file_id}")
    assert res_sv2.status_code == 403, "Other student must be forbidden from accessing file"

    # GVCN request
    api_client.logout()
    api_client.login_as_gvcn("gvcn001")
    res_gvcn = api_client.get(f"/api/v1/files/{file_id}")
    assert res_gvcn.status_code == 403, "GVCN must be forbidden from accessing individual evidence files"

    # Owner student request
    api_client.logout()
    api_client.login_as_student("sv001")
    res_owner = api_client.get(f"/api/v1/files/{file_id}")
    assert res_owner.status_code == 200

    # BCS request
    api_client.logout()
    api_client.login_as_bcs("bcs001")
    res_bcs = api_client.get(f"/api/v1/files/{file_id}")
    assert res_bcs.status_code == 200
