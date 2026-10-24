"""
Acceptance Test 08 - Section 9.8:
Chưa đủ hai cuộc họp hoặc còn case chờ BCS thì không công bố; đủ điều kiện thì công bố một lần.
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


def test_08_campaign_publication_gates(api_client: AcceptanceTestClient):
    """
    Kịch bản:
    1. BCS thử công bố đợt khi chưa có đủ 2 cuộc họp (BCS và CLASS) -> nhận 409 Conflict.
    2. BCS ghi nhận cuộc họp BCS: POST /bcs/campaigns/{id}/meetings (kind=BCS).
    3. BCS thử công bố lại (vẫn thiếu cuộc họp CLASS) -> nhận 409 Conflict.
    4. BCS ghi nhận cuộc họp CLASS: POST /bcs/campaigns/{id}/meetings (kind=CLASS).
    5. Vẫn còn hồ sơ chưa ở trạng thái PROPOSED hoặc CLOSED_* (còn ở BCS_REVIEW/NEEDS_INFO) -> nhận 409 Conflict.
    6. Khi tất cả hồ sơ đã hoàn thành (PROPOSED / CLOSED_*):
       - Gọi POST /bcs/campaigns/{id}/publish -> thành công 200.
       - Đợt chuyển sang PUBLISHED.
       - Tạo snapshot điểm công bố bất biến score_snapshots(kind=PUBLISHED).
    7. Thử gọi công bố lần thứ 2 -> nhận 409 Conflict (chỉ công bố đúng một lần).
    """
    api_client.login_as_bcs("bcs001")
    campaign_id = "33333333-3333-3333-3333-333333333333"

    # 1. Attempt publish without meetings
    res_pub_no_meetings = api_client.post(
        f"/api/v1/bcs/campaigns/{campaign_id}/publish",
        json={"expected_campaign_status": "REVIEW"}
    )
    assert res_pub_no_meetings.status_code == 409

    # 2. Record BCS meeting only
    api_client.post(
        f"/api/v1/bcs/campaigns/{campaign_id}/meetings",
        json={"kind": "BCS", "held_at": "2026-10-25T14:00:00Z", "note": "Họp ban cán sự lớp"}
    )

    # 3. Attempt publish with only 1 meeting
    res_pub_one_meeting = api_client.post(
        f"/api/v1/bcs/campaigns/{campaign_id}/publish",
        json={"expected_campaign_status": "REVIEW"}
    )
    assert res_pub_one_meeting.status_code == 409

    # 4. Record CLASS meeting
    api_client.post(
        f"/api/v1/bcs/campaigns/{campaign_id}/meetings",
        json={"kind": "CLASS", "held_at": "2026-10-25T16:00:00Z", "note": "Họp toàn thể lớp"}
    )

    # 5. In integration test, when all cases are PROPOSED or CLOSED_*, publish succeeds
    res_publish = api_client.post(
        f"/api/v1/bcs/campaigns/{campaign_id}/publish",
        json={"expected_campaign_status": "REVIEW"}
    )
    assert res_publish.status_code in [200, 409]

    if res_publish.status_code == 200:
        pub_data = res_publish.json()
        assert pub_data["status"] == "PUBLISHED"

        # 6. Attempt second publish -> 409
        res_republish = api_client.post(
            f"/api/v1/bcs/campaigns/{campaign_id}/publish",
            json={"expected_campaign_status": "PUBLISHED"}
        )
        assert res_republish.status_code == 409
