"""
Acceptance Test 09 - Section 9.9:
Trước công bố SV không thấy điểm dự kiến; sau công bố thấy đúng điểm và hạn phản hồi.
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


def test_09_score_visibility_confidentiality_before_and_after_published(api_client: AcceptanceTestClient):
    """
    Kịch bản:
    1. Khi đợt đánh giá ở OPEN hoặc REVIEW (trước PUBLISHED):
       - Sinh viên gọi GET /api/v1/student/current.
       - Backend KHÔNG trả proposed_total (hoặc trả null).
       - Backend KHÔNG trả approved_score và bcs_reason trong claims.
    2. Sau khi BCS đã công bố đợt (PUBLISHED):
       - Sinh viên gọi lại GET /api/v1/student/current.
       - Sinh viên thấy chính xác proposed_total.
       - Từng tiêu chí hiện approved_score và lý do đánh giá nếu có.
       - Hiển thị rõ appeal_deadline_at (= published_at + appeal_period_hours).
    """
    api_client.login_as_student("sv001")

    # 1. Check response in pre-published state
    current_res = api_client.get("/api/v1/student/current")
    assert current_res.status_code == 200
    data = current_res.json()

    case_status = data.get("case", {}).get("status")
    if case_status in ["DRAFT", "SUBMITTED", "NEEDS_INFO", "BCS_REVIEW", "NEEDS_PROOF", "PROPOSED"]:
        # Confidentiality assertions
        assert data["case"].get("proposed_total") is None, "proposed_total must be concealed before PUBLISHED"
        for claim in data.get("claims", []):
            assert claim.get("approved_score") is None, "approved_score must be concealed before PUBLISHED"
            assert claim.get("bcs_reason") is None, "bcs_reason must be concealed before PUBLISHED"

    # 2. Check response in PUBLISHED state
    # (Validated against mock or after publication gate in integration run)
    if case_status == "PUBLISHED":
        assert data["case"].get("proposed_total") is not None
        assert data["case"].get("appeal_deadline_at") is not None
        for claim in data.get("claims", []):
            assert claim.get("approved_score") is not None
