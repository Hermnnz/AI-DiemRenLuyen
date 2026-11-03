"""Wake the persisted review queue after submission without holding up the UI."""

import asyncio
import logging
from datetime import datetime
from time import monotonic
from asyncio import sleep

from api.app.database import SessionLocal
from api.app.models.entities import AiReviewRun
from api.app.services.ai_review_service import run_ai_tick


logger = logging.getLogger(__name__)
BACKGROUND_REVIEW_SECONDS = 240


async def process_submitted_review(run_id: str) -> None:
    """Use fresh sessions and the queue lease; retries keep their saved backoff.

    Work is already committed before this function is scheduled. If the hosting
    process stops, the existing internal AI tick can reclaim the persisted job.
    """
    try:
        await asyncio.wait_for(_process_queued_review(run_id), timeout=BACKGROUND_REVIEW_SECONDS)
    except Exception:
        # Covers both worker and session-creation errors after the submission
        # response. Its committed queue record remains available for recovery.
        logger.exception("Automatic evidence review interrupted: run=%s", run_id)


async def _process_queued_review(run_id: str) -> None:
    deadline = monotonic() + BACKGROUND_REVIEW_SECONDS
    # The queue owns the retry/attempt limit. A poll which claims no work (for
    # example, a timer waking just before the lease expires) is not an attempt.
    while monotonic() < deadline:
        with SessionLocal() as db:
            run = db.query(AiReviewRun).filter(AiReviewRun.id == run_id).first()
            if not run or run.status not in {"QUEUED", "RUNNING"}:
                return
            if run.status == "RUNNING" and (not run.lease_until or run.lease_until > datetime.utcnow()):
                return
            retry_at = run.lease_until
        delay = max(0.0, (retry_at - datetime.utcnow()).total_seconds()) if retry_at else 0.0
        remaining = deadline - monotonic()
        if delay >= remaining:
            return
        if delay:
            await sleep(min(delay + 0.01, remaining))
            # Timers can wake early; re-read the lease rather than spending a
            # retry iteration on an ineligible job.
            continue
        with SessionLocal() as db:
            result = await run_ai_tick(db, target_run_id=run_id)
        if not result["processed"]:
            # Another worker may have claimed it, or the lease can equal now.
            # Avoid a busy loop; the next read handles the updated job state.
            await sleep(0.01)
