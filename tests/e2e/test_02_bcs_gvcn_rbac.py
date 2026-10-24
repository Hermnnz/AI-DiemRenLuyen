"""
Acceptance Test 02 - Section 9.2:
BCS lớp A không mở được case lớp B; GVCN không gọi API sửa điểm.
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


def test_02_bcs_cross_class_isolation_and_gvcn_readonly(api_client: AcceptanceTestClient):
    """
    Kịch bản:
    1. BCS bcs001 thuộc Lớp A (LOP-DEMO) đăng nhập.
    2. Thử truy cập hồ sơ thuộc Lớp B (class_id khác) -> nhận 403/404.
    3. Thử xem danh sách hồ sơ đợt của Lớp B -> nhận 403/404.
    4. GVCN gvcn001 đăng nhập.
    5. GVCN gọi API chấm điểm PUT /bcs/cases/{caseId}/claims/{criterionId}/review -> nhận 403.
    6. GVCN gọi API giải quyết khiếu nại POST /bcs/appeals/{appealId}/resolve -> nhận 403.
    """
    # 1. Login as BCS of Class A
    api_client.login_as_bcs("bcs001")

    class_b_case_id = "99999999-9999-9999-9999-999999999999"
    class_b_campaign_id = "88888888-8888-8888-8888-888888888888"

    # 2. BCS tries to inspect Class B case
    res_b_case = api_client.get(f"/api/v1/bcs/cases/{class_b_case_id}")
    assert res_b_case.status_code in [403, 404]

    # 3. BCS tries to view cases of Class B campaign
    res_b_camp = api_client.get(f"/api/v1/bcs/campaigns/{class_b_campaign_id}/cases")
    assert res_b_camp.status_code in [403, 404]

    # 4. Login as GVCN
    api_client.logout()
    api_client.login_as_gvcn("gvcn001")

    # 5. GVCN attempts to modify score
    demo_case_id = "22222222-2222-2222-2222-222222222001"
    demo_criterion_id = "44444444-4444-4444-4444-444444444001"
    gvcn_edit_res = api_client.put(
        f"/api/v1/bcs/cases/{demo_case_id}/claims/{demo_criterion_id}/review",
        json={"approved_score": "10.00", "reason": "GVCN sửa điểm", "expected_version": 1}
    )
    assert gvcn_edit_res.status_code == 403, "GVCN must be forbidden from editing scores"

    # 6. GVCN attempts to resolve appeal
    gvcn_resolve_res = api_client.post(
        f"/api/v1/bcs/appeals/77777777-7777-7777-7777-777777777001/resolve",
        json={"resolution": "KEEP", "reason": "GVCN xử lý khiếu nại"}
    )
    assert gvcn_resolve_res.status_code == 403, "GVCN must be forbidden from resolving appeals"
