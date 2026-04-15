from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from celery.utils.log import get_task_logger
from redis import Redis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.market_research.snapshot import MarketResearchSnapshot
from app.services.market_research_snapshot_service import (
    get_or_create_sync_state,
    snapshot_max_item_id,
    upsert_snapshot_items,
)
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


def _build_podio_client() -> PodioClient:
    if not settings.PODIO_CLIENT_ID or not settings.PODIO_CLIENT_SECRET or not settings.PODIO_APP_ID or not settings.PODIO_APP_TOKEN:
        raise RuntimeError("Podio credentials are required for market research sync")
    return PodioClient(
        client_id=settings.PODIO_CLIENT_ID,
        client_secret=settings.PODIO_CLIENT_SECRET,
        app_id=settings.PODIO_APP_ID,
        app_token=settings.PODIO_APP_TOKEN,
    )


def _run_sync(db: Session, full_sync: bool) -> dict:
    podio_client = _build_podio_client()

    page_size = max(1, min(settings.PODIO_MR_SYNC_PAGE_SIZE, 500))
    offset = 0
    all_mapped: List = []
    known_max_id = None if full_sync else snapshot_max_item_id(db)
    incremental_max_pages = max(1, settings.PODIO_MR_INCREMENTAL_MAX_PAGES)
    pages = 0

    while True:
        items = podio_client.get_app_items(limit=page_size, offset=offset)
        if not items:
            break
        raw_mapped = [map_podio_item_to_market_research(item) for item in items if isinstance(item, dict)]
        pages += 1

        if full_sync or known_max_id is None:
            mapped = raw_mapped
        else:
            mapped = [m for m in raw_mapped if m.item_id and int(m.item_id) > int(known_max_id)]
            hit_checkpoint = len(mapped) < len(raw_mapped)
            all_mapped.extend(mapped)
            logger.info(
                "MR incremental page: offset=%s fetched=%s new=%s known_max_id=%s",
                offset,
                len(raw_mapped),
                len(mapped),
                known_max_id,
            )
            if hit_checkpoint or pages >= incremental_max_pages:
                break
            if len(items) < page_size:
                break
            offset += len(items)
            continue

        all_mapped.extend(mapped)
        logger.info("MR full sync page fetched: offset=%s fetched=%s", offset, len(mapped))
        if len(items) < page_size:
            break
        offset += len(items)

    upserted = upsert_snapshot_items(db, all_mapped, prune_missing=full_sync)
    db.commit()
    total_rows = int(db.query(MarketResearchSnapshot).count())
    return {"upserted": upserted, "total_rows": total_rows, "full_sync": full_sync, "pages": pages}


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

        # Incremental mode for frequent runs. Falls back to full behavior automatically if snapshot is empty.
        is_empty = db.query(MarketResearchSnapshot).count() == 0
        result = _run_sync(db, full_sync=is_empty)
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


@celery.task(name="podio.sync_market_research_snapshot_full")
def sync_market_research_snapshot_full() -> dict:
    redis_client = _redis_client()
    lock_acquired = True
    lock_value = datetime.now(timezone.utc).isoformat()
    if redis_client is not None:
        lock_acquired = bool(redis_client.set(_LOCK_KEY, lock_value, nx=True, ex=_LOCK_TTL_SECONDS))
    if not lock_acquired:
        logger.info("Skipping MR full sync because lock is already held")
        return {"ok": True, "skipped": True, "reason": "lock_held"}

    db = SessionLocal()
    try:
        state = get_or_create_sync_state(db)
        state.last_run_at = datetime.now(timezone.utc)
        state.last_error = None
        db.flush()

        result = _run_sync(db, full_sync=True)
        state.last_success_at = datetime.now(timezone.utc)
        state.last_synced_items = result["total_rows"]
        state.last_error = None
        db.commit()
        logger.info("MR full sync completed: upserted=%s total_rows=%s", result["upserted"], result["total_rows"])
        return {"ok": True, **result}
    except Exception as exc:
        db.rollback()
        state = get_or_create_sync_state(db)
        state.last_run_at = datetime.now(timezone.utc)
        state.last_error = str(exc)[:500]
        db.commit()
        logger.exception("MR full sync failed")
        raise
    finally:
        db.close()
        if redis_client is not None:
            current = redis_client.get(_LOCK_KEY)
            if current == lock_value:
                redis_client.delete(_LOCK_KEY)
