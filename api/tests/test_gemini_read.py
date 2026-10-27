import asyncio
import hashlib
import json

import httpx
import pytest

from api.app.review.gemini_read import GeminiReadError, GeminiReadProvider


def test_gemini_read_parses_cited_facts_without_real_api_call():
    data = b"synthetic-image"
    sha256 = hashlib.sha256(data).hexdigest()

    def handle(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-goog-api-key"] == "test-key"
        payload = json.loads(request.content)
        assert payload["generationConfig"]["responseMimeType"] == "application/json"
        assert payload["contents"][0]["parts"][0]["inline_data"]["mime_type"] == "image/png"
        extracted = {
            "readable": True,
            "unreadable_reason": "",
            "facts": [{"kind": "activity_name", "value": "Hội thảo A", "page": 1,
                       "source_excerpt": "Hội thảo A"}],
        }
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": json.dumps(extracted)}]}}]})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await GeminiReadProvider("test-key", client=client).read("file-1", sha256, "image/png", data)

    result = asyncio.run(run())
    assert result["evidence_file_id"] == "file-1"
    assert result["facts"][0]["page"] == 1


def test_gemini_read_rejects_changed_file_before_model_call():
    async def run():
        await GeminiReadProvider("test-key").read("file-1", "0" * 64, "image/png", b"changed")

    with pytest.raises(GeminiReadError) as exc:
        asyncio.run(run())
    assert exc.value.code == "EVIDENCE_HASH_MISMATCH"


def test_gemini_rate_limit_is_retryable():
    data = b"synthetic-image"

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(429))) as client:
            await GeminiReadProvider("test-key", client=client).read(
                "file-1", hashlib.sha256(data).hexdigest(), "image/png", data,
            )

    with pytest.raises(GeminiReadError) as exc:
        asyncio.run(run())
    assert exc.value.code == "MODEL_RATE_LIMITED"
    assert exc.value.retryable is True


def test_gemini_read_retries_transient_503_then_completes(monkeypatch):
    data = b"synthetic-image"
    attempts = 0

    async def no_wait(_seconds):
        pass

    monkeypatch.setattr("api.app.review.gemini_read.asyncio.sleep", no_wait)

    def respond(_request):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, json={"error": {"status": "UNAVAILABLE"}})
        extracted = {
            "readable": True,
            "unreadable_reason": "",
            "facts": [{"kind": "activity_name", "value": "Hội thảo A", "page": 1,
                       "source_excerpt": "Hội thảo A"}],
        }
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": json.dumps(extracted)}]}}]})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await GeminiReadProvider("test-key", client=client).read(
                "file-1", hashlib.sha256(data).hexdigest(), "image/png", data,
            )

    result = asyncio.run(run())
    assert attempts == 2
    assert result["readable"] is True
    assert result["facts"][0]["value"] == "Hội thảo A"

