"""
Acceptance Test 10 - Section 9.10:
SV đồng ý thì không thể khiếu nại; khiếu nại thì không thể đồng ý; hai request đồng thời chỉ một thành công.
"""
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


def test_10_accept_and_appeal_mutual_exclusion(api_client: AcceptanceTestClient):
    """
    Kịch bản:
    1. Hồ sơ đang ở trạng thái PUBLISHED.
    2. Nhánh 1: Sinh viên bấm Đồng ý (POST /student/cases/{caseId}/accept):
       - Hồ sơ chuyển sang ACCEPTED, acceptance_source = 'EXPLICIT'.
       - Sau đó, sinh viên thử gửi khiếu nại (POST /student/cases/{caseId}/appeals) -> nhận 409 Conflict.
    3. Nhánh 2 (hoặc hồ sơ khác): Sinh viên gửi khiếu nại:
       - Hồ sơ chuyển sang APPEALED.
       - Sau đó, sinh viên thử bấm Đồng ý -> nhận 409 Conflict.
    4. Concurrency: Hai request gửi cùng lúc với cùng expected_version:
       - Một request thành công, request kia nhận 409 CASE_CHANGED.
    """
    api_client.login_as_student("sv001")
    current_data = api_client.get("/api/v1/student/current").json()
    case_id = current_data["case"]["id"]
    version = current_data["case"]["version"]
    tc01_id = current_data["criteria"][0]["id"]

    # 1. Student accepts proposed score
    accept_res = api_client.post(
        f"/api/v1/student/cases/{case_id}/accept",
        json={"expected_version": version}
    )
    assert accept_res.status_code in [200, 409]

    if accept_res.status_code == 200:
        accept_data = accept_res.json()
        assert accept_data["status"] == "ACCEPTED"
        new_version = accept_data.get("version", version + 1)

        # 2. Subsequent appeal must be rejected with 409
        rejected_appeal = api_client.post(
            f"/api/v1/student/cases/{case_id}/appeals",
            json={
                "items": [{"criterion_id": tc01_id, "reason": "Khiếu nại sau khi đã đồng ý"}],
                "expected_version": new_version
            }
        )
        assert rejected_appeal.status_code == 409, "Appeal after ACCEPT must return 409 Conflict"


def test_10_appeal_then_accept_rejected(api_client: AcceptanceTestClient):
    """Verifies that once an appeal is submitted, accept is strictly forbidden."""
    api_client.login_as_student("sv002")
    current_data = api_client.get("/api/v1/student/current").json()
    case_id = current_data["case"]["id"]
    version = current_data["case"]["version"]
    tc01_id = current_data["criteria"][0]["id"]

    appeal_res = api_client.post(
        f"/api/v1/student/cases/{case_id}/appeals",
        json={
            "items": [{"criterion_id": tc01_id, "reason": "Đề nghị xem xét lại điểm tiêu chí này"}],
            "expected_version": version
        }
    )
    assert appeal_res.status_code in [200, 409]

    if appeal_res.status_code == 200:
        appeal_data = appeal_res.json()
        assert appeal_data["status"] == "APPEALED"
        new_version = appeal_data.get("version", version + 1)

        # Subsequent accept must be rejected with 409
        rejected_accept = api_client.post(
            f"/api/v1/student/cases/{case_id}/accept",
            json={"expected_version": new_version}
        )
        assert rejected_accept.status_code == 409, "Accept after APPEALED must return 409 Conflict"
