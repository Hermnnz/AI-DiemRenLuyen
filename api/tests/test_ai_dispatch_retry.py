"""Worker timing regressions: no network and no real waits."""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import sessionmaker

from api.tests.test_automatic_ai_submission import automatic_submission
from api.app.models.entities import AiReviewRun
from api.app.review.gemini_read import GeminiReadError
from api.app.services import ai_review_dispatch as dispatch
from api.app.services import ai_review_service as service


@pytest.mark.parametrize("early_wakeup", [True, False])
def test_worker_reaches_human_fallback_despite_unproductive_polls(
    db, automatic_submission, monkeypatch, early_wakeup
):
    case, _, _, _, _ = automatic_submission
    case.status = "BCS_REVIEW"
    db.commit()
    run = service.enqueue_ai_review(db, case, case.student_id, automatic=True)
    start = datetime.utcnow()
    clock = [start]
    waits = []
    provider_calls = []
    polls = []

    class Clock(datetime):
        @classmethod
        def utcnow(cls):
            return clock[0]

        @classmethod
        def now(cls, tz=None):
            return clock[0].replace(tzinfo=timezone.utc).astimezone(tz) if tz else clock[0]

    async def fake_sleep(delay):
        waits.append(delay)
        # Reproduce early Windows timer wakes beyond the old three-poll cap.
        elapsed = max(0, delay - 0.02) if early_wakeup and len(waits) <= 4 else delay
        clock[0] += timedelta(seconds=elapsed)

    async def unavailable(self, *_args):
        provider_calls.append(clock[0])
        raise GeminiReadError("MODEL_TEMPORARILY_UNAVAILABLE", retryable=True)

    original_tick = service.run_ai_tick

    async def tick(db, **kwargs):
        polls.append(clock[0])
        # A lost claim / unproductive poll must not consume a provider attempt.
        if not early_wakeup and len(polls) <= 4:
            return {"processed": 0}
        return await original_tick(db, **kwargs)

    if early_wakeup:
        run.lease_until = start + timedelta(seconds=1)
        db.commit()
    monkeypatch.setattr(dispatch, "datetime", Clock)
    monkeypatch.setattr(service, "datetime", Clock)
    monkeypatch.setattr(dispatch, "monotonic", lambda: (clock[0] - start).total_seconds())
    monkeypatch.setattr(dispatch, "sleep", fake_sleep)
    monkeypatch.setattr(dispatch, "run_ai_tick", tick)
    monkeypatch.setattr(dispatch, "SessionLocal", sessionmaker(bind=db.get_bind()))
    monkeypatch.setattr(service.GeminiReadProvider, "read", unavailable)

    asyncio.run(dispatch.process_submitted_review(run.id))
    db.expire_all()
    run = db.get(AiReviewRun, run.id)
    assert run.status == "NEEDS_HUMAN"
    assert run.error_code == "MODEL_TEMPORARILY_UNAVAILABLE"
    assert run.attempt_count == len(provider_calls) == 3
    assert run.lease_until is None
    assert case.status == "BCS_REVIEW"
    assert (provider_calls[1] - provider_calls[0]).total_seconds() >= 60
    assert (provider_calls[2] - provider_calls[1]).total_seconds() >= 120
    assert (clock[0] - start).total_seconds() < dispatch.BACKGROUND_REVIEW_SECONDS
