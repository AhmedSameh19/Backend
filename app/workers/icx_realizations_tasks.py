from __future__ import annotations

from celery.utils.log import get_task_logger

from app.core.config import settings
from app.db.session import SessionLocal
from app.repositories.expa_icx_realizations_repository import sync_icx_realizations_for_lc
from app.services.expa_icx_realizations_client import ExpaICXRealizationsClient
from app.services.expa_icx_realizations_mapper import icx_realizations_to_rows
from app.workers.celery_app import celery

from datetime import date, timedelta

logger = get_task_logger(__name__)

AIESEC_API_URL = settings.AIESEC_API_URL
AIESEC_API_TOKEN = settings.AIESEC_API_TOKEN

PER_PAGE = settings.EXPA_PER_PAGE
HOST_LC_IDS = settings.EXPA_ICX_HOST_LC_IDS
REALIZED_FROM_DATE = settings.EXPA_ICX_REALIZED_FROM


@celery.task(name="expa.fetch_icx_realizations")
def fetch_icx_realizations_hourly() -> dict:
    """Parent task that triggers sub-tasks for each host LC (fan-out)."""
    if not HOST_LC_IDS:
        logger.warning("No HOST_LC_IDS configured for iCX realizations sync.")
        return {"ok": False, "count": 0}

    for host_lc_id in HOST_LC_IDS:
        sync_icx_realization_for_lc_task.delay(host_lc_id)

    logger.info("Dispatched %s sync tasks for iCX realizations.", len(HOST_LC_IDS))
    return {"ok": True, "dispatched": len(HOST_LC_IDS)}


@celery.task(
    name="expa.sync_icx_realization_for_lc",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=5,
)
def sync_icx_realization_for_lc_task(self, host_lc_id: str) -> dict:
    """Worker task to sync iCX realizations for a specific host LC."""
    if not AIESEC_API_URL or not AIESEC_API_TOKEN:
        raise RuntimeError("AIESEC_API configuration missing")

    client = ExpaICXRealizationsClient(api_url=AIESEC_API_URL, api_token=AIESEC_API_TOKEN, timeout_seconds=60)

    start_date = date.fromisoformat(REALIZED_FROM_DATE)
    end_date = date.today()

    all_lc_rows = []
    
    def fetch_window(dt_from: date, dt_to: date):
        rows_batch = []
        page = 1
        while True:
            realizations = client.fetch_icx_realizations_page(
                from_date=dt_from.isoformat(),
                per_page=PER_PAGE,
                page=page,
                opportunity_committee=host_lc_id,
            )
            if not realizations:
                break

            mapped = icx_realizations_to_rows(realizations, host_lc_id=host_lc_id)
            if mapped:
                rows_batch.extend(mapped)

            if len(realizations) < PER_PAGE:
                break
            page += 1
        return rows_batch

    try:
        all_lc_rows = fetch_window(start_date, end_date)
    except Exception as e:
        logger.error("Host LC %s | Failed to fetch iCX realizations: %s", host_lc_id, e)
        raise

    # Process DB Sync
    db = SessionLocal()
    try:
        stats = sync_icx_realizations_for_lc(db, all_lc_rows, host_lc_id=str(host_lc_id))
        db.commit()
        logger.info("Host LC %s | iCX Realizations Sync | rows=%s | upserted=%s | deleted=%s", host_lc_id, len(all_lc_rows), stats["upserted"], stats["deleted"])
        return {"host_lc_id": host_lc_id, "rows": len(all_lc_rows), **stats}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
