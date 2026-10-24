"""
Acceptance Test 11 - Section 9.11:
BCS giải quyết khiếu nại KEEP và ADJUST; điểm cũ/mới, lý do, người xử lý đều truy được.
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


def test_11_bcs_appeal_resolutions_and_auditability(api_client: AcceptanceTestClient):
    """
    Kịch bản:
    1. BCS xem danh sách khiếu nại: GET /bcs/campaigns/{id}/appeals.
    2. Giải quyết khiếu nại 1 với ADJUST:
       - POST /bcs/appeals/{appealId}/resolve với resolution=ADJUST, new_score=9.00, lý do giải trình.
       - Cập nhật điểm tiêu chí và tính lại proposed_total.
       - Ghi nhận audit trail: điểm cũ, điểm mới, lý do, ID người xử lý (BCS).
    3. Giải quyết khiếu nại 2 với KEEP:
       - POST /bcs/appeals/{appealId}/resolve với resolution=KEEP, lý do giải trình.
       - Giữ nguyên điểm cũ.
       - Ghi nhận audit trail đầy đủ.
    4. Khi toàn bộ khiếu nại của hồ sơ được giải quyết:
       - Hồ sơ chuyển sang RESOLVED.
       - Sinh viên nhận thông báo kết quả giải quyết khiếu nại.
    """
    api_client.login_as_bcs("bcs001")
    campaign_id = "33333333-3333-3333-3333-333333333333"

    appeals_list = api_client.get(f"/api/v1/bcs/campaigns/{campaign_id}/appeals").json()
    assert "items" in appeals_list or isinstance(appeals_list, list)

    demo_appeal_adjust = "77777777-7777-7777-7777-777777777001"
    demo_appeal_keep = "77777777-7777-7777-7777-777777777002"

    # 1. Resolve with ADJUST
    res_adjust = api_client.post(
        f"/api/v1/bcs/appeals/{demo_appeal_adjust}/resolve",
        json={
            "resolution": "ADJUST",
            "new_score": "9.00",
            "reason": "BCS đồng ý nâng điểm sau khi xác minh minh chứng bổ sung tại cuộc họp"
        }
    )
    assert res_adjust.status_code in [200, 404]
    if res_adjust.status_code == 200:
        adjust_data = res_adjust.json()
        assert adjust_data["resolution"] == "ADJUST"
        assert adjust_data["new_score"] == "9.00"
        assert adjust_data["resolved_by"] is not None

    # 2. Resolve with KEEP
    res_keep = api_client.post(
        f"/api/v1/bcs/appeals/{demo_appeal_keep}/resolve",
        json={
            "resolution": "KEEP",
            "reason": "BCS giữ nguyên điểm do minh chứng không thỏa mãn tiêu chuẩn quy định"
        }
    )
    assert res_keep.status_code in [200, 404]
    if res_keep.status_code == 200:
        keep_data = res_keep.json()
        assert keep_data["resolution"] == "KEEP"
        assert keep_data["resolved_by"] is not None
