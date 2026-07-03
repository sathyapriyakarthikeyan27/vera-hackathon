"""
Celery task for the RAG freshness loop.

`rag.reverify_sources` (Beat, periodic) re-crawls every registered source and lets the
pipeline's change detection do its job:
  - unchanged  -> last_verified bumped, stays 'active'
  - changed    -> chunks refreshed, facts re-staged UNVERIFIED, source -> 'pending_review'
  - error      -> source -> 'error', last_error recorded

Crucially this task never publishes a changed eligibility number. It surfaces the change
(status 'pending_review' + a log line) so a human reviews it via the pending-facts queue.
Screening policy moves slowly, so this runs on a slow cadence (default weekly).

Like tasks/reminders.py, the worker is a separate sync process from the FastAPI app, so
it opens and closes its own asyncpg pool per run rather than sharing the app's.
"""

import asyncio
import logging

from celery_app import celery

logger = logging.getLogger(__name__)


async def _reverify_all() -> dict:
    # Import inside the coroutine so the module imports cleanly in the worker even
    # before a DB/loop exists.
    from services.database import close_pool
    from services.ingestion.pipeline import ingest_registry
    from services.ingestion.registry import all_sources

    registry = all_sources()  # every jurisdiction (UK, India, ...)
    try:
        results = await ingest_registry(registry, force=False)
    finally:
        await close_pool()

    summary: dict = {"total": len(results)}
    for r in results:
        summary[r["status"]] = summary.get(r["status"], 0) + 1
    changed = [r["source_key"] for r in results if r["status"] == "changed"]
    errored = [r["source_key"] for r in results if r["status"] == "error"]
    if changed:
        logger.warning("RAG re-verify: %d source(s) CHANGED, awaiting review: %s", len(changed), changed)
    if errored:
        logger.warning("RAG re-verify: %d source(s) errored: %s", len(errored), errored)
    logger.info("RAG re-verify complete: %s", summary)
    return summary


@celery.task(name="rag.reverify_sources")
def reverify_sources() -> dict:
    return asyncio.run(_reverify_all())
