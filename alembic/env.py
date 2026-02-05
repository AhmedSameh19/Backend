from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from app.core.config import settings

# this is the Alembic Config object, which provides access to the values within the .ini file
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import your Base + models so metadata is populated
from app.db.base import Base  # noqa
from app.models.leads.expa_lead_comments import ExpaLeadComment
from app.models.leads.expa_lead_snapshot import ExpaLeadStatusSnapshot
from app.models.members import Member
from app.models.leads.expa_leads import ExpaLead  # noqa: F401  (ensures models are imported)
from app.models.market_research.igv import IGVMarketResearch  # noqa: F401
from app.models.market_research.b2b_market_research import B2BMarketResearch  # noqa: F401
from app.models.market_research.podio_scheduled_visit import PodioScheduledVisit  # noqa: F401
from app.models.google_calendar_token import GoogleCalendarToken  # noqa: F401
from app.models.icx.expa_icx_leads import ExpaICXLead  # noqa: F401
from app.models.icx.expa_icx_lead_comments import ExpaICXLeadComment  # noqa: F401
from app.models.icx.expa_icx_lead_followups import ExpaICXLeadFollowUp  # noqa: F401
from app.models.icx.expa_icx_lead_status_snapshot import ExpaICXLeadStatusSnapshot  # noqa: F401
from app.models.icx.expa_icx_realizations import ExpaICXRealization  # noqa: F401
from app.models.icx.icx_realizations_standards import ICXRealizationsStandards  # noqa: F401
from app.models.ogx.ogx_standards import OgxStandards  # noqa: F401

target_metadata = Base.metadata



def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


def get_url():
    url = settings.DATABASE_URL
    if not url:
        raise RuntimeError("DB_URL not set in environment/.env")
    return url
run_migrations_online()
