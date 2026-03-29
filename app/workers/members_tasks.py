from celery.utils.log import get_task_logger

from datetime import date

from app.core.config import settings
from app.db.session import SessionLocal
from app.repositories.members_repository import upsert_members
from app.services.expa_client import ExpaClient
from app.services.expa__members_mapper import members_to_rows
from app.workers.celery_app import celery

logger = get_task_logger(__name__)

AIESEC_API_URL = settings.AIESEC_API_URL
AIESEC_API_TOKEN = settings.AIESEC_API_TOKEN

LC_CODES = settings.EXPA_LC_CODES
HOME_MC_ID = settings.EXPA_HOME_MC_ID
LC_NAMES = settings.EXPA_LC_NAMES


def _aiesec_year_range(today: date) -> tuple[str, str]:
    """
    AIESEC year:
      - Feb 1 .. Feb 1 (next year), end is exclusive (covers through Jan 31).
    """
    feb1_this_year = date(today.year, 2, 1)

    if today >= feb1_this_year:
        start = feb1_this_year
        end = date(today.year + 1, 2, 1)
    else:
        start = date(today.year - 1, 2, 1)
        end = feb1_this_year

    return start.isoformat(), end.isoformat()


@celery.task(name="expa.fetch_members_monthly")
def fetch_members_monthly() -> dict:
    if not AIESEC_API_URL:
        raise RuntimeError("AIESEC_API_URL is not set")
    if not AIESEC_API_TOKEN:
        raise RuntimeError("AIESEC_API_TOKEN is not set")

    client = ExpaClient(api_url=AIESEC_API_URL, api_token=AIESEC_API_TOKEN, timeout_seconds=60)
    from_date, to_date = _aiesec_year_range(date.today())

    grand_total = 0

    for lc_code in LC_CODES:
        logger.info("Fetching members for LC %s | range %s..%s", lc_code, from_date, to_date)

        members = client.fetch_members(home_lc_id=lc_code, from_date=from_date, to_date=to_date)
        if not members:
            continue
        rows = members_to_rows(
            members,
            home_lc_id=lc_code,
            home_mc_id=HOME_MC_ID,
            home_lc_name=LC_NAMES.get(lc_code) if isinstance(LC_NAMES, dict) else str(lc_code),
        )
        if not rows:
            continue

        db = SessionLocal()
        try:
            from app.repositories.members_repository import sync_members_for_lc
            stats = sync_members_for_lc(db, rows, home_lc_id=str(lc_code))
            db.commit()
            upserted = stats["upserted"]
            deleted = stats["deleted"]
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

        grand_total += upserted
        logger.info("LC %s | fetched=%s | upserted=%s | deleted=%s", lc_code, len(members), upserted, deleted)

    logger.info("Finished members monthly | total_upserted=%s", grand_total)
    return {"ok": True, "total_upserted": grand_total, "from": from_date, "to": to_date}
