from __future__ import annotations
from datetime import date, timedelta
from celery.utils.log import get_task_logger

from app.core.config import settings
from app.db.session import SessionLocal
from app.repositories.expa_leads_repository import sync_leads_for_lc
from app.services.expa_client import ExpaClient
from app.services.expa_leads_mapper import people_to_rows
from app.workers.celery_app import celery

logger = get_task_logger(__name__)

AIESEC_API_URL = settings.AIESEC_API_URL
AIESEC_API_TOKEN = settings.AIESEC_API_TOKEN

REGISTERED_FROM = settings.EXPA_REGISTERED_FROM
REGISTERED_TO = settings.EXPA_REGISTERED_TO
PER_PAGE = settings.EXPA_PER_PAGE
LC_CODES = settings.EXPA_LC_CODES
HOME_MC_ID = settings.EXPA_HOME_MC_ID


@celery.task(name="expa.fetch_people")
def fetch_people_hourly() -> dict:
    """Parent task that triggers sub-tasks for each Local Committee (fan-out)."""
    if not LC_CODES:
        logger.warning("No LC_CODES configured for people sync.")
        return {"ok": False, "count": 0}

    for lc_code in LC_CODES:
        sync_people_for_lc_task.delay(lc_code)

    logger.info("Dispatched %s sync tasks for people leads.", len(LC_CODES))
    return {"ok": True, "dispatched": len(LC_CODES)}


@celery.task(
    name="expa.sync_people_for_lc",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=5,
)
def sync_people_for_lc_task(self, lc_code: int) -> dict:
    """Worker task to sync leads for a specific LC. Includes adaptive windowing."""
    if not AIESEC_API_URL or not AIESEC_API_TOKEN:
        raise RuntimeError("AIESEC_API configuration missing")

    client = ExpaClient(api_url=AIESEC_API_URL, api_token=AIESEC_API_TOKEN, timeout_seconds=60)

    start_date = date.fromisoformat(REGISTERED_FROM)
    end_date = date.fromisoformat(REGISTERED_TO)

    all_lc_rows = []
    
    # Adaptive Windowing Logic
    def fetch_window(dt_from: date, dt_to: date):
        rows_batch = []
        page = 1
        while True:
            people = client.fetch_people_page(
                home_committee=lc_code,
                registered_from=dt_from.isoformat(),
                registered_to=dt_to.isoformat(),
                per_page=PER_PAGE,
                page=page,
            )
            if not people:
                break

            mapped = people_to_rows(people, home_committee_id=lc_code, home_mc_id=HOME_MC_ID)
            if mapped:
                rows_batch.extend(mapped)

            if len(people) < PER_PAGE:
                break
            page += 1
        return rows_batch

    current_start = start_date
    slice_days = 366  # Start by trying the whole year

    while current_start <= end_date:
        current_end = min(current_start + timedelta(days=slice_days - 1), end_date)
        try:
            batch = fetch_window(current_start, current_end)
            all_lc_rows.extend(batch)
            current_start = current_end + timedelta(days=1)
        except Exception as e:
            # If the window is too large or times out, shrink and retry
            if slice_days > 7:
                slice_days = max(7, slice_days // 4)
                logger.warning("LC %s | timeout/error; shrinking window to %s days", lc_code, slice_days)
                continue
            else:
                logger.error("LC %s | Failed to sync window %s to %s: %s", lc_code, current_start, current_end, e)
                raise # Let celery handle the task retry

    # Process DB Sync
    db = SessionLocal()
    try:
        stats = sync_leads_for_lc(db, all_lc_rows, home_lc_id=int(lc_code))
        db.commit()
        logger.info("LC %s | Final Sync | rows=%s | upserted=%s | deleted=%s", lc_code, len(all_lc_rows), stats["upserted"], stats["deleted"])
        return {"lc": lc_code, "rows": len(all_lc_rows), **stats}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
