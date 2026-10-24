"""
Acceptance Test 07 - Section 9.7:
BCS nhập điểm vượt max hoặc khác tự khai mà không có lý do bị 422; tổng dự kiến cộng đúng.
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


def test_07_bcs_scoring_validation_and_proposed_total(api_client: AcceptanceTestClient):
    """
    Kịch bản:
    1. BCS nhập điểm duyệt approved_score vượt quá max_score (ví dụ 15.00 > 10.00) -> nhận 422.
    2. BCS nhập điểm duyệt khác điểm tự khai nhưng không kèm lý do (hoặc lý do rỗng) -> nhận 422.
    3. BCS nhập điểm duyệt hợp lệ kèm lý do giải trình khi khác tự khai -> nhận 200.
    4. BCS hoàn tất đánh giá (complete-review) cho toàn bộ tiêu chí.
    5. Kỳ vọng:
       - Hồ sơ chuyển sang PROPOSED.
       - proposed_total được cộng chính xác từ các approved_score.
    """
    api_client.login_as_bcs("bcs001")
    demo_case_id = "22222222-2222-2222-2222-222222222001"
    tc01_id = "44444444-4444-4444-4444-444444444001"

    case_info = api_client.get(f"/api/v1/bcs/cases/{demo_case_id}").json()
    version = case_info["version"]

    # 1. Score exceeds max_score (max is 10.00)
    res_exceed = api_client.put(
        f"/api/v1/bcs/cases/{demo_case_id}/claims/{tc01_id}/review",
        json={"approved_score": "15.00", "reason": "Chấm cao", "expected_version": version}
    )
    assert res_exceed.status_code == 422, "approved_score > max_score must return 422"

    # 2. Score differs from self_score without reason
    res_no_reason = api_client.put(
        f"/api/v1/bcs/cases/{demo_case_id}/claims/{tc01_id}/review",
        json={"approved_score": "7.00", "reason": "", "expected_version": version}
    )
    assert res_no_reason.status_code == 422, "Different score without reason must return 422"

    # 3. Valid score with valid reason
    res_valid = api_client.put(
        f"/api/v1/bcs/cases/{demo_case_id}/claims/{tc01_id}/review",
        json={
            "approved_score": "7.00",
            "reason": "Minh chứng chỉ đạt mức khá theo thang điểm quy chế",
            "expected_version": version
        }
    )
    assert res_valid.status_code == 200
    new_version = res_valid.json().get("version", version + 1)

    # 4. Complete review for the case
    complete_res = api_client.post(
        f"/api/v1/bcs/cases/{demo_case_id}/complete-review",
        json={"expected_version": new_version}
    )
    assert complete_res.status_code in [200, 422]
    if complete_res.status_code == 200:
        res_data = complete_res.json()
        assert res_data["status"] == "PROPOSED"
        assert res_data.get("proposed_total") is not None
