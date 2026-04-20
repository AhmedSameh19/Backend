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
    if not AIESEC_API_URL:
        raise RuntimeError("AIESEC_API_URL is not set")
    if not AIESEC_API_TOKEN:
        raise RuntimeError("AIESEC_API_TOKEN is not set")

    client = ExpaICXLeadsClient(api_url=AIESEC_API_URL, api_token=AIESEC_API_TOKEN, timeout_seconds=60)
    all_fetched_application_ids = []

    def fetch_range(*, created_from: datetime, created_to: datetime, programmes: list[int]) -> int:
        page = 1
        total_upserted = 0

        while True:
            try:
                items = client.fetch_icx_leads_page(
                    opportunity_home_mc=HOME_MC_ID,
                    programmes=programmes,
                    created_from=created_from.isoformat(),
                    created_to=created_to.isoformat(),
                    per_page=PER_PAGE,
                    page=page,
                )
            except RuntimeError as exc:
                if _is_result_window_error(exc):
                    raise _ExpaResultWindowTooLarge(str(exc))
                raise

            if not items:
                break
            
            # Collect IDs for cleanup
            for item in items:
                if "id" in item:
                    all_fetched_application_ids.append(str(item["id"]))

            rows = icx_applications_to_rows(items)
            if not rows:
                break

            db = SessionLocal()
            try:
                upserted = upsert_expa_icx_leads(db, rows)
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()

            total_upserted += upserted
            logger.info(
                "iCX | %s → %s | page %s | fetched=%s | upserted=%s",
                created_from.date(),
                created_to.date(),
                page,
                len(items),
                upserted,
            )

            if len(items) < PER_PAGE:
                break

            if page * PER_PAGE >= 10_000:
                raise _ExpaResultWindowTooLarge("Reached page window limit for this time slice")

            page += 1

        return total_upserted

    start = _parse_iso_datetime(ICX_CREATED_FROM)
    end = datetime.now(timezone.utc)

    slice_days = 31
    grand_total = 0

    while start < end:
        slice_end = min(start + timedelta(days=slice_days), end)

        try:
            grand_total += fetch_range(created_from=start, created_to=slice_end, programmes=list(ICX_PROGRAMMES))
            start = slice_end
            slice_days = 31
        except _ExpaResultWindowTooLarge:
            if slice_days > 1:
                slice_days = max(1, slice_days // 2)
                logger.warning(
                    "iCX | result window too large; shrinking slice to %s day(s)",
                    slice_days,
                )
                continue

            logger.warning(
                "iCX | still too large at 1-day slice; splitting by programme for %s",
                start.date(),
            )

            progressed = False
            for programme in ICX_PROGRAMMES:
                grand_total += fetch_range(created_from=start, created_to=slice_end, programmes=[int(programme)])
                progressed = True

            if not progressed:
                raise

            start = slice_end
            slice_days = 31

    # Final cleanup for this MC
    db = SessionLocal()
    try:
        deleted = delete_stale_icx_leads(db, all_fetched_application_ids, str(HOME_MC_ID))
        db.commit()
        logger.info("Finished iCX leads | total_upserted=%s | deleted=%s", grand_total, deleted)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return {"ok": True, "total_upserted": grand_total, "deleted": deleted}
