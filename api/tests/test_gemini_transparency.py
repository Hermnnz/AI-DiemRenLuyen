import asyncio
import hashlib
import json

import httpx
import pytest

from api.app.review.gemini_read import GeminiReadError
from api.app.review.gemini_transparency import GeminiTransparencyProvider


DATA = b"synthetic-image"
HASH = hashlib.sha256(DATA).hexdigest()
READ = {
    "evidence_file_id": "file-1", "sha256": HASH, "readable": True,
    "unreadable_reason": "", "facts": [
        {"kind": "activity_name", "value": "Hoi thao A", "page": 1, "source_excerpt": "Hoi thao A"},
    ],
}
CRITERION = {
    "code": "7b", "title": "Hoạt động ngoài trường", "description": "Tham gia hoạt động ngoài trường",
    "evidence_notes": "Chứng nhận online hợp lệ được chấp nhận.", "rule_config": {},
    "clause_id": "49K14_1_V1:7b",
}


def _assess(answer: dict, handler=None) -> dict:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-goog-api-key"] == "test-key"
        assert request.url.path.endswith("/models/gemini-3.6-flash:generateContent")
        payload = json.loads(request.content)
        assert payload["generationConfig"]["thinkingConfig"]["thinkingLevel"] == "medium"
        assert payload["contents"][0]["parts"][1]["inline_data"]["mime_type"] == "image/png"
        return handler(request) if handler else httpx.Response(
            200, json={"candidates": [{"content": {"parts": [{"text": json.dumps(answer)}]}}]},
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await GeminiTransparencyProvider("test-key", client=client).assess(
                evidence_file_id="file-1", sha256=HASH, mime_type="image/png", data=DATA,
                read_result=READ, criterion=CRITERION, student_name="Sinh viên A", term="HK1",
            )

    return asyncio.run(run())


def test_transparency_cites_read_fact_and_does_not_claim_authenticity():
    result = _assess({
        "verdict": "SUPPORTED", "reason": "Nội dung hoạt động phù hợp.", "fact_indexes": [0],
        "visual_signals": [], "limitations": ["Chưa xác minh đơn vị cấp."],
    })
    assert result["verdict"] == "SUPPORTED"
    assert result["raw_verdict"] == "SUPPORTED"
    assert result["post_processing_reason"] is None
    assert result["citations"] == [{"page": 1, "source_excerpt": "Hoi thao A",
                                    "kind": "activity_name", "value": "Hoi thao A"}]
    assert result["rule_clause_id"] == "49K14_1_V1:7b"
    assert result["authenticity"] == "UNVERIFIED"
    assert result["requires_human_review"] is True


def test_transparency_downgrades_unsupported_verdict_and_visual_concern():
    no_citation = _assess({"verdict": "SUPPORTED", "reason": "Có vẻ phù hợp.", "fact_indexes": [],
                           "visual_signals": [], "limitations": []})
    assert no_citation["verdict"] == "UNKNOWN"
    assert no_citation["raw_verdict"] == "SUPPORTED"
    assert no_citation["post_processing_reason"] == "UNKNOWN_DUE_TO_MISSING_CITATIONS"

    suspicious = _assess({"verdict": "SUPPORTED", "reason": "Có vẻ phù hợp.", "fact_indexes": [0],
                          "visual_signals": [{"page": 1, "description": "Tên bị đè", "concern": True}],
                          "limitations": []})
    assert suspicious["verdict"] == "FLAGGED"
    assert suspicious["raw_verdict"] == "SUPPORTED"
    assert suspicious["post_processing_reason"] == "FLAGGED_DUE_TO_VISUAL_CONCERN"
    assert suspicious["authenticity"] == "SUSPICIOUS"


def test_transparency_all_verdicts_and_post_processing_branches():
    # 1. FLAGGED with no citations and no visual signals -> downgraded to UNKNOWN
    no_basis = _assess({
        "verdict": "FLAGGED", "reason": "Nghi ngờ chung chung.", "fact_indexes": [],
        "visual_signals": [], "limitations": [],
    })
    assert no_basis["verdict"] == "UNKNOWN"
    assert no_basis["raw_verdict"] == "FLAGGED"
    assert no_basis["post_processing_reason"] == "UNKNOWN_DUE_TO_LACK_OF_BASIS"

    # 2. FLAGGED with visual signals -> stays FLAGGED, post_processing_reason is None
    flagged_direct = _assess({
        "verdict": "FLAGGED", "reason": "Có dấu vết tẩy xóa.", "fact_indexes": [],
        "visual_signals": [{"page": 1, "description": "Dấu vết tẩy xóa", "concern": True}],
        "limitations": [],
    })
    assert flagged_direct["verdict"] == "FLAGGED"
    assert flagged_direct["raw_verdict"] == "FLAGGED"
    assert flagged_direct["post_processing_reason"] is None

    # 3. UNKNOWN -> stays UNKNOWN, post_processing_reason is None
    unknown_direct = _assess({
        "verdict": "UNKNOWN", "reason": "Không đủ thông tin.", "fact_indexes": [],
        "visual_signals": [], "limitations": [],
    })
    assert unknown_direct["verdict"] == "UNKNOWN"
    assert unknown_direct["raw_verdict"] == "UNKNOWN"
    assert unknown_direct["post_processing_reason"] is None


def test_transparency_rejects_fabricated_citation_and_rate_limit():
    with pytest.raises(GeminiReadError) as citation_error:
        _assess({"verdict": "SUPPORTED", "reason": "Phù hợp.", "fact_indexes": [99],
                 "visual_signals": [], "limitations": []})
    assert citation_error.value.code == "MODEL_INVALID_CITATION"

    with pytest.raises(GeminiReadError) as rate_error:
        _assess({}, handler=lambda _: httpx.Response(429))
    assert rate_error.value.code == "MODEL_RATE_LIMITED"
    assert rate_error.value.retryable is True


def test_transparency_retries_transient_503_then_completes(monkeypatch):
    attempts = 0

    async def no_wait(_seconds):
        pass

    monkeypatch.setattr("api.app.review.gemini_transparency.asyncio.sleep", no_wait)

    def respond(_request):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, json={"error": {"status": "UNAVAILABLE"}})
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": json.dumps({
            "verdict": "FLAGGED", "reason": "Tệp ghi mẫu giả lập.", "fact_indexes": [0],
            "visual_signals": [], "limitations": ["Chưa xác minh nguồn cấp."],
        })}]}}]})

    result = _assess({}, handler=respond)
    assert attempts == 2
    assert result["verdict"] == "FLAGGED"


def test_transparency_stops_after_bounded_server_retries(monkeypatch):
    attempts = 0

    async def no_wait(_seconds):
        pass

    monkeypatch.setattr("api.app.review.gemini_transparency.asyncio.sleep", no_wait)

    def unavailable(_request):
        nonlocal attempts
        attempts += 1
        return httpx.Response(503, json={"error": {"status": "UNAVAILABLE"}})

    with pytest.raises(GeminiReadError) as error:
        _assess({}, handler=unavailable)
    assert attempts == 3
    assert error.value.code == "MODEL_TEMPORARILY_UNAVAILABLE"
    assert error.value.retryable is True
