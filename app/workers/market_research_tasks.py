from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from celery.utils.log import get_task_logger
from redis import Redis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.market_research.snapshot import MarketResearchSnapshot
from app.services.market_research_snapshot_service import get_or_create_sync_state, upsert_snapshot_items
from app.services.podio_client import PodioClient
from app.api.v1.endpoints.market_research import map_podio_item_to_market_research
from app.workers.celery_app import celery

logger = get_task_logger(__name__)

_LOCK_KEY = "mr_sync_lock"
_LOCK_TTL_SECONDS = 60 * 4


def _redis_client() -> Redis | None:
    if not settings.REDIS_URL:
        return None
    return Redis.from_url(settings.REDIS_URL, decode_responses=True)


def _run_sync(db: Session) -> dict:
    if not settings.PODIO_CLIENT_ID or not settings.PODIO_CLIENT_SECRET or not settings.PODIO_APP_ID or not settings.PODIO_APP_TOKEN:
        raise RuntimeError("Podio credentials are required for market research sync")

    podio_client = PodioClient(
        client_id=settings.PODIO_CLIENT_ID,
        client_secret=settings.PODIO_CLIENT_SECRET,
        app_id=settings.PODIO_APP_ID,
        app_token=settings.PODIO_APP_TOKEN,
    )

    page_size = max(1, min(settings.PODIO_MR_SYNC_PAGE_SIZE, 500))
    offset = 0
    all_mapped = []

    while True:
        items = podio_client.get_app_items(limit=page_size, offset=offset)
        if not items:
            break
        mapped = [map_podio_item_to_market_research(item) for item in items if isinstance(item, dict)]
        all_mapped.extend(mapped)
        logger.info("MR sync page fetched: offset=%s fetched=%s", offset, len(mapped))
        if len(items) < page_size:
            break
        offset += len(items)

    upserted = upsert_snapshot_items(db, all_mapped, prune_missing=True)
    db.commit()
    total_rows = int(db.query(MarketResearchSnapshot).count())
    return {"upserted": upserted, "total_rows": total_rows}


@celery.task(name="podio.sync_market_research_snapshot")
def sync_market_research_snapshot() -> dict:
    redis_client = _redis_client()
    lock_acquired = True
    lock_value = datetime.now(timezone.utc).isoformat()
    if redis_client is not None:
        lock_acquired = bool(redis_client.set(_LOCK_KEY, lock_value, nx=True, ex=_LOCK_TTL_SECONDS))

    if not lock_acquired:
        logger.info("Skipping MR sync because lock is already held")
        return {"ok": True, "skipped": True, "reason": "lock_held"}

    db = SessionLocal()
    try:
        state = get_or_create_sync_state(db)
        state.last_run_at = datetime.now(timezone.utc)
        state.last_error = None
        db.flush()

        result = _run_sync(db)
        state.last_success_at = datetime.now(timezone.utc)
        state.last_synced_items = result["total_rows"]
        state.last_error = None
        db.commit()
        logger.info("MR sync completed: upserted=%s total_rows=%s", result["upserted"], result["total_rows"])
        return {"ok": True, **result}
    except Exception as exc:
        db.rollback()
        state = get_or_create_sync_state(db)
        state.last_run_at = datetime.now(timezone.utc)
        state.last_error = str(exc)[:500]
        db.commit()
        logger.exception("MR sync failed")
        raise
    finally:
        db.close()
        if redis_client is not None:
            current = redis_client.get(_LOCK_KEY)
            if current == lock_value:
                redis_client.delete(_LOCK_KEY)
