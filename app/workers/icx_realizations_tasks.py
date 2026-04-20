from __future__ import annotations

from celery.utils.log import get_task_logger

from app.core.config import settings
from app.db.session import SessionLocal
from app.repositories.expa_icx_realizations_repository import sync_icx_realizations_for_lc
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

    grand_total_upserted = 0
    grand_total_deleted = 0

    for host_lc_id in HOST_LC_IDS:
        logger.info("Fetching iCX realizations for host LC %s", host_lc_id)

        page = 1
        all_lc_rows = []

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
            if rows:
                all_lc_rows.extend(rows)

            if len(realizations) < PER_PAGE:
                break

            page += 1

        # Perform sync for this Host LC
        db = SessionLocal()
        try:
            stats = sync_icx_realizations_for_lc(db, all_lc_rows, host_lc_id=str(host_lc_id))
            db.commit()
            upserted = stats["upserted"]
            deleted = stats["deleted"]
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

        logger.info("host_lc_id %s | rows=%s | upserted=%s | deleted=%s", host_lc_id, len(all_lc_rows), upserted, deleted)
        grand_total_upserted += upserted
        grand_total_deleted += deleted

    logger.info("Finished iCX realizations ALL host LCs | total_upserted=%s | total_deleted=%s", grand_total_upserted, grand_total_deleted)
    return {"ok": True, "total_upserted": grand_total_upserted, "total_deleted": grand_total_deleted, "from": REALIZED_FROM_DATE}
