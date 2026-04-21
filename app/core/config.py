from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


def _env_int(name: str, default: int) -> int:
    raw = _env(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as e:
        raise RuntimeError(f"{name} must be an int (got {raw!r})") from e


def _env_int_optional(name: str) -> Optional[int]:
    raw = _env(name)
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _env_json_lc_option_ids(name: str) -> Optional[Dict[str, List[int]]]:
    """Parse env like PODIO_LC_OPTION_IDS='{"899":[123,456]}' -> {"899": [123, 456]}."""
    raw = _env(name)
    if not raw or not raw.strip():
        if name == "PODIO_LC_OPTION_IDS":
            # Default mapping for Accelerator Egypt production Podio app (Local Committee field).
            # If Coolify omits PODIO_LC_OPTION_IDS, LC-filtered reads would otherwise return empty.
            raw = (
                '{"1609":[19],"1789":[1],"5688":[26],"257":[2],"1064":[3],"2820":[4],'
                '"1788":[6],"2124":[7],"1114":[8],"171":[9],"109":[10],"1725":[11],'
                '"899":[12],"1727":[13],"2126":[14],"2818":[15],"2125":[16],"15":[17],'
                '"2817":[21],"1489":[22],"6683":[28]}'
            )
        else:
            return None
    candidates = [raw]
    if '\\"' in raw:
        candidates.append(raw.replace('\\"', '"'))
    if raw.startswith('"') and raw.endswith('"'):
        candidates.append(raw[1:-1])

    for candidate in candidates:
        try:
            data = json.loads(candidate)
            if not isinstance(data, dict):
                continue
            out: Dict[str, List[int]] = {}
            for k, v in data.items():
                if isinstance(v, list):
                    out[str(k)] = [int(x) for x in v if isinstance(x, (int, float))]
                elif isinstance(part_v := v, (int, float)):
                    out[str(k)] = [int(part_v)]
            if out:
                return out
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
    return None


def _env_csv_ints(name: str, default: List[int]) -> List[int]:
    raw = _env(name)
    if not raw:
        return default
    items: List[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            items.append(int(part))
        except ValueError as e:
            raise RuntimeError(f"{name} must be comma-separated ints (bad value: {part!r})") from e
    return items or default


def _normalize_origin(origin: str) -> str:
    origin = origin.strip()
    if origin == "*":
        return origin
    return origin.rstrip("/")


@dataclass(frozen=True)
class Settings:
    # Infrastructure (Celery)
    RABBITMQ_URL: Optional[str]
    REDIS_URL: Optional[str]

    # URLs
    FRONTEND_URL: str
    BACKEND_URL: str

    CORS_ORIGINS: List[str]

    # Database
    DATABASE_URL: Optional[str]
    DB_POOL_SIZE: int
    DB_MAX_OVERFLOW: int
    DB_POOL_TIMEOUT: int
    DB_CONNECT_TIMEOUT: int

    # EXPA/AIESEC
    AIESEC_API_URL: Optional[str]
    AIESEC_API_TOKEN: Optional[str]

    EXPA_REGISTERED_FROM: str
    EXPA_REGISTERED_TO: str
    EXPA_APPROVED_FROM: str
    EXPA_PER_PAGE: int
    EXPA_LC_CODES: List[int]
    EXPA_HOME_MC_ID: int
    EXPA_LC_NAMES: Optional[dict]

    EXPA_ICX_CREATED_FROM: str
    EXPA_ICX_PROGRAMMES: List[int]
    EXPA_ICX_HOST_LC_IDS: List[int]
    EXPA_ICX_REALIZED_FROM: str

    # Podio
    PODIO_CLIENT_ID: Optional[str]
    PODIO_CLIENT_SECRET: Optional[str]
    PODIO_APP_ID: Optional[str]
    PODIO_APP_TOKEN: Optional[str]
    PODIO_WEBFORM_URL: str  # For proxy embedding (e.g. https://podio.com/webforms/25879454/1936053)
    PODIO_FIELD_ASSIGNED_TO: str  # Podio field external_id for "assigned to" (e.g. assigned-to)
    # Optional: Podio filter by LC (faster than fetch-all then filter). Set to use POST /item/app/{id}/filter/
    PODIO_MARKET_RESEARCH_LC_FIELD_ID: Optional[int]  # Podio field_id for Local Committee (category)
    PODIO_LC_OPTION_IDS: Optional[Dict[str, List[int]]]  # e.g. {"899": [123, 456]} = lc_id 899 -> Podio category option ids
    PODIO_MR_SYNC_INTERVAL_MINUTES: int
    PODIO_MR_SYNC_PAGE_SIZE: int
    PODIO_MR_INCREMENTAL_MAX_PAGES: int
    PODIO_MR_FULL_SYNC_HOURS: int
    PODIO_MR_ENABLE_FULL_SYNC_BEAT: bool
    PODIO_MR_FULL_SYNC_COOLDOWN_MINUTES: int

    # Google Calendar
    GOOGLE_CLIENT_ID: Optional[str]
    GOOGLE_CLIENT_SECRET: Optional[str]
    GOOGLE_CALENDAR_REDIRECT_URI: Optional[str]

    # Email / SMTP
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: str
    SMTP_FROM_EMAIL: str
    SMTP_FROM_NAME: str
    SMTP_USE_TLS: bool

    @staticmethod
    def from_env() -> "Settings":
        default_lc_codes = [
            2820, 1788, 1322, 1789, 899, 1489, 2126, 1064, 109,
            5688, 257, 2124, 171, 1727, 2125, 2817, 2818, 15,
            1725, 1114, 6683
        ]
        default_lc_codes_names = {
            2820: "6th October University",
            1788: "AAST Alexandria",
            1322: "AAST in Cairo",
            1789: "Ain Shams University",
            899: "Alexandria",
            1489: "AUC",
            2126: "Beni Suef",
            1064: "Cairo University",
            109: "Damietta",
            5688: "Galala",
            257: "GUC",
            2124: "Helwan",
            171: "Mansoura",
            1727: "Menofia",
            2125: "MIU",
            2817: "MSA",
            2818: "MUST",
            15: "Suez",
            1725: "Tanta",
            1114: "Zagazig",
            6683: "New Capital",
            1609: "MC Egypt"
        }

        _cors_raw = _env("CORS_ORIGINS", "https://accelerator.aiesec.org.eg,http://localhost:3000")
        cors_origins = [_normalize_origin(o) for o in _cors_raw.split(",") if o.strip()]

        frontend_url = _env("FRONTEND_URL", "https://accelerator.aiesec.org.eg").rstrip("/")
        backend_url = _env("BACKEND_URL", "https://api-accelerator.aiesec.org.eg").rstrip("/")

        return Settings(
            RABBITMQ_URL=_env("RABBITMQ_URL"),
            REDIS_URL=_env("REDIS_URL"),
            FRONTEND_URL=frontend_url,
            BACKEND_URL=backend_url,
            CORS_ORIGINS=cors_origins,
            DATABASE_URL=_env("DATABASE_URL") or _env("DB_URL"),
            DB_POOL_SIZE=_env_int("DB_POOL_SIZE", 5),
            DB_MAX_OVERFLOW=_env_int("DB_MAX_OVERFLOW", 0),
            DB_POOL_TIMEOUT=_env_int("DB_POOL_TIMEOUT", 5),
            DB_CONNECT_TIMEOUT=_env_int("DB_CONNECT_TIMEOUT", 5),
            AIESEC_API_URL=_env("AIESEC_API_URL"),
            AIESEC_API_TOKEN=_env("AIESEC_API_TOKEN"),
            EXPA_REGISTERED_FROM=_env("EXPA_REGISTERED_FROM", "2026-01-01") or "2026-01-01",
            EXPA_REGISTERED_TO=_env("EXPA_REGISTERED_TO", "2026-12-31") or "2026-12-31",
            EXPA_APPROVED_FROM=_env("EXPA_APPROVED_FROM", "2026-01-01") or "2026-01-01",
            EXPA_PER_PAGE=_env_int("EXPA_PER_PAGE", 100),
            EXPA_LC_CODES=_env_csv_ints("EXPA_LC_CODES", default_lc_codes),
            EXPA_LC_NAMES=default_lc_codes_names,
            EXPA_HOME_MC_ID=_env_int("EXPA_HOME_MC_ID", 1609),
            EXPA_ICX_CREATED_FROM=_env("EXPA_ICX_CREATED_FROM", "2026-01-01") or "2026-01-01",
            EXPA_ICX_PROGRAMMES=_env_csv_ints("EXPA_ICX_PROGRAMMES", [7, 8, 9]),
            EXPA_ICX_HOST_LC_IDS=_env_csv_ints("EXPA_ICX_HOST_LC_IDS", default_lc_codes),
            EXPA_ICX_REALIZED_FROM=_env("EXPA_ICX_REALIZED_FROM", "2026-01-01") or "2026-01-01",
            PODIO_CLIENT_ID=_env("PODIO_CLIENT_ID"),
            PODIO_CLIENT_SECRET=_env("PODIO_CLIENT_SECRET"),
            PODIO_APP_ID=_env("PODIO_APP_ID"),
            PODIO_APP_TOKEN=_env("PODIO_APP_TOKEN"),
            PODIO_WEBFORM_URL=_env(
                "PODIO_WEBFORM_URL",
                "https://podio.com/webforms/25879454/1936053",
            ) or "https://podio.com/webforms/25879454/1936053",
            PODIO_FIELD_ASSIGNED_TO=_env("PODIO_FIELD_ASSIGNED_TO", "assigned-to") or "assigned-to",
            PODIO_MARKET_RESEARCH_LC_FIELD_ID=_env_int_optional("PODIO_MARKET_RESEARCH_LC_FIELD_ID") or 221098564,
            PODIO_LC_OPTION_IDS=_env_json_lc_option_ids("PODIO_LC_OPTION_IDS"),
            PODIO_MR_SYNC_INTERVAL_MINUTES=_env_int("PODIO_MR_SYNC_INTERVAL_MINUTES", 5),
            PODIO_MR_SYNC_PAGE_SIZE=_env_int("PODIO_MR_SYNC_PAGE_SIZE", 500),
            PODIO_MR_INCREMENTAL_MAX_PAGES=_env_int("PODIO_MR_INCREMENTAL_MAX_PAGES", 10),
            PODIO_MR_FULL_SYNC_HOURS=_env_int("PODIO_MR_FULL_SYNC_HOURS", 6),
            PODIO_MR_ENABLE_FULL_SYNC_BEAT=(_env("PODIO_MR_ENABLE_FULL_SYNC_BEAT", "false") or "false").lower() in ("true", "1", "yes"),
            PODIO_MR_FULL_SYNC_COOLDOWN_MINUTES=_env_int("PODIO_MR_FULL_SYNC_COOLDOWN_MINUTES", 30),
            GOOGLE_CLIENT_ID=_env("GOOGLE_CLIENT_ID"),
            GOOGLE_CLIENT_SECRET=_env("GOOGLE_CLIENT_SECRET"),
            GOOGLE_CALENDAR_REDIRECT_URI=_env("GOOGLE_CALENDAR_REDIRECT_URI"),
            SMTP_HOST=_env("SMTP_HOST", "smtp.gmail.com") or "smtp.gmail.com",
            SMTP_PORT=_env_int("SMTP_PORT", 587),
            SMTP_USER=_env("SMTP_USER", "") or "",
            SMTP_PASSWORD=_env("SMTP_PASSWORD", "") or "",
            SMTP_FROM_EMAIL=_env("SMTP_FROM_EMAIL", "") or "",
            SMTP_FROM_NAME=_env("SMTP_FROM_NAME", "AIESEC CRM") or "AIESEC CRM",
            SMTP_USE_TLS=(_env("SMTP_USE_TLS", "true") or "true").lower() in ("true", "1", "yes"),
        )


settings = Settings.from_env()