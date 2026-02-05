from __future__ import annotations

from celery.utils.log import get_task_logger

from app.core.config import settings
from app.db.session import SessionLocal
from app.repositories.expa_icx_realizations_repository import upsert_icx_realizations
from app.services.expa_icx_realizations_client import ExpaICXRealizationsClient
from app.services.expa_icx_realizations_mapper import icx_realizations_to_rows
from app.workers.celery_app import celery

logger = get_task_logger(__name__)

AIESEC_API_URL = settings.AIESEC_API_URL
AIESEC_API_TOKEN = settings.AIESEC_API_TOKEN

PER_PAGE = settings.EXPA_PER_PAGE
HOST_LC_IDS = settings.EXPA_ICX_HOST_LC_IDS
REALIZED_FROM_DATE = settings.EXPA_ICX_REALIZED_FROM


@celery.task(name="expa.fetch_icx_realizations")
def fetch_icx_realizations_hourly() -> dict:
    if not AIESEC_API_URL:
        raise RuntimeError("AIESEC_API_URL is not set")
    if not AIESEC_API_TOKEN:
        raise RuntimeError("AIESEC_API_TOKEN is not set")

    client = ExpaICXRealizationsClient(api_url=AIESEC_API_URL, api_token=AIESEC_API_TOKEN, timeout_seconds=60)

    grand_total = 0

    for host_lc_id in HOST_LC_IDS:
        logger.info("Fetching iCX realizations for host LC %s", host_lc_id)

        page = 1
        lc_total = 0

        while True:
            realizations = client.fetch_icx_realizations_page(
                from_date=REALIZED_FROM_DATE,
                per_page=PER_PAGE,
                page=page,
                opportunity_committee=host_lc_id,
            )

            if not realizations:
                break

            rows = icx_realizations_to_rows(realizations, host_lc_id=host_lc_id)
            if not rows:
                if len(realizations) < PER_PAGE:
                    break
                page += 1
                continue

            db = SessionLocal()
            try:
                upserted = upsert_icx_realizations(db, rows)
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()

            lc_total += upserted
            logger.info(
                "host_lc_id %s | page %s | fetched=%s | upserted=%s",
                host_lc_id,
                page,
                len(realizations),
                upserted,
            )

            if len(realizations) < PER_PAGE:
                break

            page += 1

        logger.info("Finished iCX realizations host_lc_id %s | total_upserted=%s", host_lc_id, lc_total)
        grand_total += lc_total

    logger.info("Finished iCX realizations ALL host LCs | grand_total_upserted=%s", grand_total)
    return {"ok": True, "total_upserted": grand_total, "from": REALIZED_FROM_DATE}
