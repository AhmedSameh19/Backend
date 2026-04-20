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
    if not AIESEC_API_URL:
        raise RuntimeError("AIESEC_API_URL is not set")
    if not AIESEC_API_TOKEN:
        raise RuntimeError("AIESEC_API_TOKEN is not set")

    client = ExpaClient(api_url=AIESEC_API_URL, api_token=AIESEC_API_TOKEN, timeout_seconds=60)

    grand_total_upserted = 0
    grand_total_deleted = 0

    for lc_code in LC_CODES:
        logger.info("Fetching people for LC %s", lc_code)

        page = 1
        all_lc_rows = []

        while True:
            people = client.fetch_people_page(
                home_committee=lc_code,
                registered_from=REGISTERED_FROM,
                registered_to=REGISTERED_TO,
                per_page=PER_PAGE,
                page=page,
            )

            if not people:
                break

            rows = people_to_rows(people, home_committee_id=lc_code, home_mc_id=HOME_MC_ID)
            if rows:
                all_lc_rows.extend(rows)

            if len(people) < PER_PAGE:
                break

            page += 1

        # Perform sync for this LC
        db = SessionLocal()
        try:
            stats = sync_leads_for_lc(db, all_lc_rows, home_lc_id=int(lc_code))
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

    logger.info("Finished ALL LCs | total_upserted=%s | total_deleted=%s", grand_total_upserted, grand_total_deleted)
    return {"ok": True, "total_upserted": grand_total_upserted, "total_deleted": grand_total_deleted}
