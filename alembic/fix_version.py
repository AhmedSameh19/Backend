"""
One-time script: fix alembic_version when DB has a revision ID that no longer
exists in the codebase (e.g. f3c4d5e6f7a8). Sets version to e1f2a3b4c5d6 so
"alembic upgrade head" can run and create google_calendar_tokens.

Run from Backend folder with venv active:
  python alembic/fix_version.py

Then run: python -m alembic upgrade head
"""
import os
import sys

from pathlib import Path
backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend))
from dotenv import load_dotenv
load_dotenv(backend / ".env")

database_url = os.getenv("DATABASE_URL") or os.getenv("DB_URL")
if not database_url:
    print("ERROR: DATABASE_URL or DB_URL not set in .env")
    sys.exit(1)

# psycopg expects postgresql://, not postgresql+psycopg://
if database_url.startswith("postgresql+psycopg"):
    database_url = "postgresql" + database_url[len("postgresql+psycopg"):]

try:
    import psycopg
except ImportError:
    print("ERROR: pip install psycopg")
    sys.exit(1)

conn = psycopg.connect(database_url, autocommit=True)
cur = conn.cursor()

cur.execute("SELECT version_num FROM alembic_version")
row = cur.fetchone()
known = (
    "3d6b5e310e1e", "ac7be3f84e53", "4219ec4ce561", "4e69770c6f23", "238c5de6f01e",
    "9343f1b7e665", "6da9e63f510e", "5fa0178c80d0", "b0e31a323dbc", "7a57a8863ed7",
    "933dc07d1926", "b400251ef8a3", "000f7e6e91a5", "a9b12d66df4d", "c8f3e9a1b2d4",
    "e1f2a3b4c5d6", "f2a3b4c5d6e7",
)
if not row:
    print("No row in alembic_version. Inserting e1f2a3b4c5d6.")
    cur.execute("INSERT INTO alembic_version (version_num) VALUES (%s)", ("e1f2a3b4c5d6",))
else:
    current = row[0]
    print(f"Current alembic_version: {current}")
    if current not in known:
        cur.execute("UPDATE alembic_version SET version_num = %s WHERE version_num = %s", ("e1f2a3b4c5d6", current))
        print(f"Updated to e1f2a3b4c5d6 so next 'alembic upgrade head' will create google_calendar_tokens.")
    else:
        print("Version already known. No change.")

cur.close()
conn.close()
print("Done. Now run: python -m alembic upgrade head")
