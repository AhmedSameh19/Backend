from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

_mr_sync_interval_minutes = max(1, int(settings.PODIO_MR_SYNC_INTERVAL_MINUTES))

broker = settings.RABBITMQ_URL
backend = settings.REDIS_URL
if not broker:
    raise RuntimeError("RABBITMQ_URL is not set. Check your .env")
if not backend:
    raise RuntimeError("REDISs_URL is not set. Check your .env")


celery = Celery(
    "crm_workers",
    broker=broker,
    backend=backend,
    include=[
        "app.workers.people_tasks",
        "app.workers.members_tasks",
        "app.workers.realizations_tasks",
        "app.workers.icx_leads_tasks",
        "app.workers.icx_realizations_tasks",
        "app.workers.followup_reminder_tasks",
        "app.workers.market_research_tasks",
    ],
)

celery.conf.update(
    timezone="Africa/Cairo",
    enable_utc=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
)

celery.conf.beat_schedule = {
    "fetch-expa-people-every-hour": {
        "task": "expa.fetch_people",
        "schedule": crontab(minute=0),  # at minute 0 of every hour
    },
    "fetch-expa-icx-leads-every-hour": {
        "task": "expa.fetch_icx_leads",
        "schedule": crontab(minute=0),  # at minute 0 of every hour
    },
    "fetch-expa-realizations-every-hour": {
        "task": "expa.fetch_realizations",
        "schedule": crontab(minute=0),  # at minute 0 of every hour
    },
    "fetch-expa-icx-realizations-every-hour": {
        "task": "expa.fetch_icx_realizations",
        "schedule": crontab(minute=0),  # at minute 0 of every hour
    },
    "fetch-expa-members-monthly": {
        "task": "expa.fetch_members_monthly",
        "schedule": crontab(day_of_month=1, hour=0, minute=10),
    },
    "send-followup-reminders-every-15min": {
        "task": "notifications.send_followup_reminders",
        "schedule": crontab(minute="*/15"),  # every 15 minutes
    },
    "sync-podio-market-research-snapshot": {
        "task": "podio.sync_market_research_snapshot",
        "schedule": crontab(minute=f"*/{_mr_sync_interval_minutes}"),
    },
}
celery.conf.broker_connection_retry_on_startup = True

celery.autodiscover_tasks(["app.workers"])
