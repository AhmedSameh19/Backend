from celery.utils.log import get_task_logger

from app.core.config import settings
from app.db.session import SessionLocal
from app.repositories.expa_leads_repository import upsert_expa_leads
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

    grand_total = 0

    for lc_code in LC_CODES:
        logger.info("Fetching people for LC %s", lc_code)

        page = 100
        lc_total = 0

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
            if not rows:
                break

            db = SessionLocal()
            try:
                upserted = upsert_expa_leads(db, rows)
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()

            lc_total += upserted
            logger.info("LC %s | page %s | fetched=%s | upserted=%s", lc_code, page, len(people), upserted)

            if len(people) < PER_PAGE:
                break

            page += 1

        logger.info("Finished LC %s | total_upserted=%s", lc_code, lc_total)
        grand_total += lc_total

    logger.info("Finished ALL LCs | grand_total_upserted=%s", grand_total)
    return {"ok": True, "total_upserted": grand_total}
