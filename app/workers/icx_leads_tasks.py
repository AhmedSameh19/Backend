from celery.utils.log import get_task_logger

from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.db.session import SessionLocal
from app.repositories.expa_icx_leads_repository import upsert_expa_icx_leads, delete_stale_icx_leads
from app.services.expa_icx_leads_client import ExpaICXLeadsClient
from app.services.expa_icx_leads_mapper import icx_applications_to_rows
from app.workers.celery_app import celery

logger = get_task_logger(__name__)

AIESEC_API_URL = settings.AIESEC_API_URL
AIESEC_API_TOKEN = settings.AIESEC_API_TOKEN

PER_PAGE = settings.EXPA_PER_PAGE
HOME_MC_ID = settings.EXPA_HOME_MC_ID
ICX_CREATED_FROM = settings.EXPA_ICX_CREATED_FROM
ICX_PROGRAMMES = settings.EXPA_ICX_PROGRAMMES


class _ExpaResultWindowTooLarge(RuntimeError):
    pass


def _parse_iso_datetime(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _is_result_window_error(exc: Exception) -> bool:
    msg = str(exc)
    return "max_result_window" in msg or "Result window is too large" in msg


@celery.task(name="expa.fetch_icx_leads")
def fetch_icx_leads_hourly() -> dict:
    """Parent task that triggers sub-tasks for each month for iCX leads (fan-out)."""
    start_date = _parse_iso_datetime(ICX_CREATED_FROM)
    end_date = datetime.now(timezone.utc)
    
    # Fan out by month
    current = start_date
    dispatched = 0
    while current < end_date:
        next_month = (current.replace(day=1) + timedelta(days=32)).replace(day=1)
        window_end = min(next_month - timedelta(seconds=1), end_date)
        
        sync_icx_leads_for_window_task.delay(
            current.isoformat(), 
            window_end.isoformat()
        )
        
        current = next_month
        dispatched += 1

    logger.info("Dispatched %s iCX sync tasks (by month).", dispatched)
    return {"ok": True, "dispatched": dispatched}


@celery.task(
    name="expa.sync_icx_leads_for_window",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=5,
)
def sync_icx_leads_for_window_task(self, dt_from_iso: str, dt_to_iso: str) -> dict:
    """Worker task to sync iCX leads for a specific time window."""
    if not AIESEC_API_URL or not AIESEC_API_TOKEN:
        raise RuntimeError("AIESEC_API configuration missing")

    client = ExpaICXLeadsClient(api_url=AIESEC_API_URL, api_token=AIESEC_API_TOKEN, timeout_seconds=60)
    
    dt_from = _parse_iso_datetime(dt_from_iso)
    dt_to = _parse_iso_datetime(dt_to_iso)
    
    fetched_ids = []
    total_upserted = 0
    
    def fetch_window(window_from: datetime, window_to: datetime, programmes: list[int]):
        page = 1
        batch_upserted = 0
        while True:
            try:
                items = client.fetch_icx_leads_page(
                    opportunity_home_mc=HOME_MC_ID,
                    programmes=programmes,
                    created_from=window_from.isoformat(),
                    created_to=window_to.isoformat(),
                    per_page=PER_PAGE,
                    page=page,
                )
            except RuntimeError as exc:
                if _is_result_window_error(exc):
                    raise _ExpaResultWindowTooLarge(str(exc))
                raise

            if not items:
                break
                
            for item in items:
                if "id" in item:
                    fetched_ids.append(str(item["id"]))

            rows = icx_applications_to_rows(items)
            if rows:
                db = SessionLocal()
                try:
                    upserted = upsert_expa_icx_leads(db, rows)
                    db.commit()
                    batch_upserted += upserted
                except Exception:
                    db.rollback()
                    raise
                finally:
                    db.close()

            if len(items) < PER_PAGE:
                break
            if page * PER_PAGE >= 10_000:
                raise _ExpaResultWindowTooLarge("Reached page window limit")
            page += 1
        return batch_upserted

    # Process with adaptive windowing
    current_start = dt_from
    slice_days = (dt_to - dt_from).days + 1

    while current_start < dt_to:
        current_end = min(current_start + timedelta(days=slice_days), dt_to)
        try:
            total_upserted += fetch_window(current_start, current_end, list(ICX_PROGRAMMES))
            current_start = current_end
            # Reset slice_days if it was small
            slice_days = (dt_to - dt_from).days + 1
        except _ExpaResultWindowTooLarge:
            if slice_days > 1:
                slice_days = max(1, slice_days // 2)
                logger.warning("iCX Window %s | Shrinking slice to %s days", dt_from.strftime("%Y-%m"), slice_days)
                continue
            
            # Split by programme if even 1 day is too large
            for prog in ICX_PROGRAMMES:
                total_upserted += fetch_window(current_start, current_end, [int(prog)])
            current_start = current_end
        except Exception:
            raise # Let celery retry

    # Displacement within this window
    db = SessionLocal()
    try:
        deleted = delete_stale_icx_leads(
            db, 
            fetched_ids, 
            str(HOME_MC_ID),
            created_from=dt_from_iso,
            created_to=dt_to_iso
        )
        db.commit()
        logger.info(
            "iCX Window %s - %s | Upserted: %s | Deleted: %s", 
            dt_from.date(), dt_to.date(), total_upserted, deleted
        )
        return {"upserted": total_upserted, "deleted": deleted}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

