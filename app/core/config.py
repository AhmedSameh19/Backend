from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional

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


@dataclass(frozen=True)
class Settings:
    # Infrastructure (Celery)
    RABBITMQ_URL: Optional[str]
    REDIS_URL: Optional[str]

    # Database
    DATABASE_URL: Optional[str]

    # EXPA/AIESEC
    AIESEC_API_URL: Optional[str]
    AIESEC_API_TOKEN: Optional[str]

    EXPA_REGISTERED_FROM: str
    EXPA_REGISTERED_TO: str
    EXPA_PER_PAGE: int
    EXPA_LC_CODES: List[int]
    EXPA_HOME_MC_ID: int
    EXPA_LC_NAMES: Optional[dict]
    
    # Podio
    PODIO_CLIENT_ID: Optional[str]
    PODIO_CLIENT_SECRET: Optional[str]
    PODIO_APP_ID: Optional[str]
    PODIO_APP_TOKEN: Optional[str]

    # Google Calendar
    GOOGLE_CLIENT_ID: Optional[str]
    GOOGLE_CLIENT_SECRET: Optional[str]
    GOOGLE_CALENDAR_REDIRECT_URI: Optional[str]

    @staticmethod
    def from_env() -> "Settings":
        default_lc_codes = [
            2820, 1788, 1322, 1789, 899, 1489, 2126, 1064, 109,
            5688, 257, 2124, 171, 1727, 2125, 2817, 2818, 15,
            1725, 1114, 6683,
        ]
        default_lc_codes_names={
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

        return Settings(
            RABBITMQ_URL=_env("RABBITMQ_URL"),
            REDIS_URL=_env("REDIS_URL"),
            DATABASE_URL=_env("DATABASE_URL") or _env("DB_URL"),
            AIESEC_API_URL=_env("AIESEC_API_URL"),
            AIESEC_API_TOKEN=_env("AIESEC_API_TOKEN"),
            EXPA_REGISTERED_FROM=_env("EXPA_REGISTERED_FROM", "2025-01-01") or "2025-01-01",
            EXPA_REGISTERED_TO=_env("EXPA_REGISTERED_TO", "2025-12-31") or "2025-12-31",
            EXPA_PER_PAGE=_env_int("EXPA_PER_PAGE", 100),
            EXPA_LC_CODES=_env_csv_ints("EXPA_LC_CODES", default_lc_codes),
            EXPA_LC_NAMES=default_lc_codes_names,
            EXPA_HOME_MC_ID=_env_int("EXPA_HOME_MC_ID", 1609),
            PODIO_CLIENT_ID=_env("PODIO_CLIENT_ID"),
            PODIO_CLIENT_SECRET=_env("PODIO_CLIENT_SECRET"),
            PODIO_APP_ID=_env("PODIO_APP_ID"),
            PODIO_APP_TOKEN=_env("PODIO_APP_TOKEN"),
            GOOGLE_CLIENT_ID=_env("GOOGLE_CLIENT_ID"),
            GOOGLE_CLIENT_SECRET=_env("GOOGLE_CLIENT_SECRET"),
            GOOGLE_CALENDAR_REDIRECT_URI=_env("GOOGLE_CALENDAR_REDIRECT_URI"),
        )


settings = Settings.from_env()