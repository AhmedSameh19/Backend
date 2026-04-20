from __future__ import annotations

from celery.utils.log import get_task_logger

from app.core.config import settings
from app.db.session import SessionLocal
from app.repositories.expa_realizations_repository import sync_realizations_for_lc
from app.services.expa_realizations_client import ExpaRealizationsClient
from app.services.expa_realizations_mapper import realizations_to_rows
from app.workers.celery_app import celery

logger = get_task_logger(__name__)

AIESEC_API_URL = settings.AIESEC_API_URL
AIESEC_API_TOKEN = settings.AIESEC_API_TOKEN

PER_PAGE = settings.EXPA_PER_PAGE
LC_CODES = settings.EXPA_LC_CODES

APPROVED_FROM_DATE = settings.EXPA_APPROVED_FROM


@celery.task(name="expa.fetch_realizations")
def fetch_realizations_hourly() -> dict:
    if not AIESEC_API_URL:
        raise RuntimeError("AIESEC_API_URL is not set")
    if not AIESEC_API_TOKEN:
        raise RuntimeError("AIESEC_API_TOKEN is not set")

    client = ExpaRealizationsClient(api_url=AIESEC_API_URL, api_token=AIESEC_API_TOKEN, timeout_seconds=60)

    grand_total_upserted = 0
    grand_total_deleted = 0

    for lc_code in LC_CODES:
        logger.info("Fetching realizations for LC %s", lc_code)

        page = 1
        all_lc_rows = []

        while True:
            realizations = client.fetch_realizations(
                person_committee=lc_code,
                from_date=APPROVED_FROM_DATE,
                per_page=PER_PAGE,
                page=page,
            )
            if not realizations:
                break

            rows = realizations_to_rows(realizations, home_committee_id=lc_code)
            if rows:
                all_lc_rows.extend(rows)

            if len(realizations) < PER_PAGE:
                break

            page += 1

        # Perform sync for this LC
        db = SessionLocal()
        try:
            stats = sync_realizations_for_lc(db, all_lc_rows, home_lc_id=int(lc_code))
            db.commit()
            upserted = stats["upserted"]
            deleted = stats["deleted"]
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

        logger.info("LC %s | rows=%s | upserted=%s | deleted=%s", lc_code, len(all_lc_rows), upserted, deleted)
        grand_total_upserted += upserted
        grand_total_deleted += deleted

    logger.info("Finished realizations ALL LCs | total_upserted=%s | total_deleted=%s", grand_total_upserted, grand_total_deleted)
    return {"ok": True, "total_upserted": grand_total_upserted, "total_deleted": grand_total_deleted, "from": APPROVED_FROM_DATE}
