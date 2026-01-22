from __future__ import annotations

from celery.utils.log import get_task_logger

from app.core.config import settings
from app.db.session import SessionLocal
from app.repositories.expa_realizations_repository import upsert_expa_realizations
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

    grand_total = 0

    for lc_code in LC_CODES:
        logger.info("Fetching realizations for LC %s", lc_code)

        page = 1
        lc_total = 0

        while True:
            realizations = client.fetch_realizations(
                person_committee=lc_code,
                from_date=APPROVED_FROM_DATE,
                per_page=PER_PAGE,
                page=page,
            )
            if not realizations:
                break

            rows = realizations_to_rows(realizations,home_committee_id=lc_code)
            if not rows:
                if len(realizations) < PER_PAGE:
                    break
                page += 1
                continue

            db = SessionLocal()
            try:
                upserted = upsert_expa_realizations(db, rows)
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()

            lc_total += upserted
            logger.info("LC %s | page %s | fetched=%s | upserted=%s", lc_code, page, len(realizations), upserted)

            if len(realizations) < PER_PAGE:
                break

            page += 1

        logger.info("Finished realizations LC %s | total_upserted=%s", lc_code, lc_total)
        grand_total += lc_total

    logger.info("Finished realizations ALL LCs | grand_total_upserted=%s", grand_total)
    return {"ok": True, "total_upserted": grand_total, "from": APPROVED_FROM_DATE}
