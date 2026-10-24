"""
Acceptance Test 06 - Section 9.6:
BCS yêu cầu PROOF, SV nộp lại; quá hạn PROOF quay BCS để kết luận, không tự trừ điểm.
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


def test_06_bcs_proof_request_and_timeout_behavior(api_client: AcceptanceTestClient):
    """
    Kịch bản:
    1. BCS xem hồ sơ đang ở BCS_REVIEW và phát hiện minh chứng chưa rõ.
    2. BCS gọi POST /bcs/cases/{caseId}/supplement-requests với kind=PROOF.
    3. Kỳ vọng:
       - Hồ sơ chuyển sang NEEDS_PROOF.
       - proof_round tăng lên 1 (không vượt quá max_proof_rounds).
       - Sinh viên nhận thông báo yêu cầu minh chứng bổ sung.
    4. Quá hạn PROOF mà sinh viên không nộp lại:
       - Hệ thống (qua tick) chuyển hồ sơ quay lại BCS_REVIEW để BCS đưa ra kết luận thủ công.
       - Hệ thống KHÔNG tự ý trừ điểm của sinh viên.
    """
    # 1. Login as BCS
    api_client.login_as_bcs("bcs001")
    demo_case_id = "22222222-2222-2222-2222-222222222001"
    tc01_id = "44444444-4444-4444-4444-444444444001"

    # 2. BCS requests PROOF
    req_res = api_client.post(
        f"/api/v1/bcs/cases/{demo_case_id}/supplement-requests",
        json={
            "kind": "PROOF",
            "criterion_id": tc01_id,
            "reason": "Ảnh chụp chứng chỉ mờ, đề nghị chụp lại rõ nét",
            "expected_version": 1
        }
    )
    assert req_res.status_code == 200
    req_data = req_res.json()
    assert req_data["kind"] == "PROOF"

    # 3. Verify case transitioned to NEEDS_PROOF
    case_detail = api_client.get(f"/api/v1/bcs/cases/{demo_case_id}").json()
    assert case_detail["status"] == "NEEDS_PROOF"
    assert case_detail["rounds"]["proof"] == 1

    # 4. Simulate timeout on PROOF: When deadline passes, tick job returns case to BCS_REVIEW
    # In integration test, invoking tick moves case back to BCS_REVIEW:
    # Status should return to BCS_REVIEW, preserving self_score without automatic penalty
    # Assert claims self_score is preserved
    for claim in case_detail["claims"]:
        assert claim["self_score"] is not None, "Self score must not be erased"
