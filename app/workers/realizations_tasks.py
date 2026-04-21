from __future__ import annotations

from celery.utils.log import get_task_logger

from app.core.config import settings
from app.db.session import SessionLocal
from app.repositories.expa_realizations_repository import sync_realizations_for_lc
from app.services.expa_realizations_client import ExpaRealizationsClient
from app.services.expa_realizations_mapper import realizations_to_rows
from app.workers.celery_app import celery

from datetime import date, timedelta

logger = get_task_logger(__name__)

AIESEC_API_URL = settings.AIESEC_API_URL
AIESEC_API_TOKEN = settings.AIESEC_API_TOKEN

PER_PAGE = settings.EXPA_PER_PAGE
LC_CODES = settings.EXPA_LC_CODES
APPROVED_FROM_DATE = settings.EXPA_APPROVED_FROM


@celery.task(name="expa.fetch_realizations")
def fetch_realizations_hourly() -> dict:
    """Parent task that triggers sub-tasks for each Local Committee (fan-out)."""
    if not LC_CODES:
        logger.warning("No LC_CODES configured for realizations sync.")
        return {"ok": False, "count": 0}

    for lc_code in LC_CODES:
        sync_realizations_for_lc_task.delay(lc_code)

    logger.info("Dispatched %s sync tasks for realizations.", len(LC_CODES))
    return {"ok": True, "dispatched": len(LC_CODES)}


@celery.task(
    name="expa.sync_realizations_for_lc",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=5,
)
def sync_realizations_for_lc_task(self, lc_code: int) -> dict:
    """Worker task to sync realizations for a specific LC. Includes adaptive windowing."""
    if not AIESEC_API_URL or not AIESEC_API_TOKEN:
        raise RuntimeError("AIESEC_API configuration missing")

    client = ExpaRealizationsClient(api_url=AIESEC_API_URL, api_token=AIESEC_API_TOKEN, timeout_seconds=60)

    start_date = date.fromisoformat(APPROVED_FROM_DATE)
    end_date = date.today()

    all_lc_rows = []
    
    def fetch_window(dt_from: date, dt_to: date):
        rows_batch = []
        page = 1
        while True:
            realizations = client.fetch_realizations(
                person_committee=lc_code,
                from_date=dt_from.isoformat(),
                # Assuming the client supports or respects a range if we modify it, 
                # but currently realizations_client only takes from_date.
                # If the API only supports from_date, we just fetch from start_date.
                per_page=PER_PAGE,
                page=page,
            )
            if not realizations:
                break

            mapped = realizations_to_rows(realizations, home_committee_id=lc_code)
            if mapped:
                rows_batch.extend(mapped)

            if len(realizations) < PER_PAGE:
                break
            page += 1
        return rows_batch

    # For realizations, the current client only supports from_date.
    # So adaptive windowing is limited to just retrying the whole batch or failing.
    # However, I'll still keep the fan-out by LC which provides massive isolation.
    
    try:
        all_lc_rows = fetch_window(start_date, end_date)
    except Exception as e:
        logger.error("LC %s | Failed to fetch realizations: %s", lc_code, e)
        raise

    # Process DB Sync
    db = SessionLocal()
    try:
        stats = sync_realizations_for_lc(db, all_lc_rows, home_lc_id=int(lc_code))
        db.commit()
        logger.info("LC %s | Realizations Sync | rows=%s | upserted=%s | deleted=%s", lc_code, len(all_lc_rows), stats["upserted"], stats["deleted"])
        return {"lc": lc_code, "rows": len(all_lc_rows), **stats}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
