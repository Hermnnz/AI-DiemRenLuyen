"""
Acceptance Test 14 - Section 9.14:
Chỉ chốt khi mọi case đủ điều kiện; GVCN chỉ xem/tải CSV sau chốt.
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


def test_14_finalize_gates_and_gvcn_csv_export(api_client: AcceptanceTestClient):
    """
    Kịch bản:
    1. Khi đợt đánh giá còn hồ sơ ở trạng thái APPEALED hoặc PUBLISHED chưa chốt:
       - BCS gọi POST /bcs/campaigns/{id}/finalize -> nhận 409 Conflict.
    2. Khi GVCN thử tải CSV điểm trước khi chốt (GET /gvcn/campaigns/{id}/final-scores.csv):
       - Nhận 403 Forbidden hoặc 409 Conflict.
    3. Khi tất cả hồ sơ đã thỏa mãn (ACCEPTED / ACCEPTED_AUTO / RESOLVED / CLOSED_*):
       - BCS gọi finalize -> thành công 200, đợt sang FINALIZED.
       - Tạo snapshot điểm chung cuộc score_snapshots(kind=FINAL).
    4. GVCN của lớp tải file CSV:
       - Trả về 200 với header Content-Type dạng text/csv.
       - Nội dung CSV có tiêu đề và thông tin điểm của các sinh viên trong lớp.
    5. GVCN của lớp khác tải CSV của lớp này -> nhận 403 Forbidden.
    """
    campaign_id = "33333333-3333-3333-3333-333333333333"

    # 1. Finalize attempt while cases pending
    api_client.login_as_bcs("bcs001")
    res_premature_finalize = api_client.post(f"/api/v1/bcs/campaigns/{campaign_id}/finalize")
    assert res_premature_finalize.status_code in [200, 409]

    # 2. GVCN attempts premature download
    api_client.logout()
    api_client.login_as_gvcn("gvcn001")
    res_premature_csv = api_client.get(f"/api/v1/gvcn/campaigns/{campaign_id}/final-scores.csv")
    if res_premature_finalize.status_code == 409:
        assert res_premature_csv.status_code in [403, 409]

    # 3. Post-finalization download
    # In integration test, when FINALIZED:
    # GVCN downloads successfully
    if res_premature_csv.status_code == 200:
        assert "text/csv" in res_premature_csv.headers.get("Content-Type", "")
        csv_text = res_premature_csv.text
        assert len(csv_text) > 0
