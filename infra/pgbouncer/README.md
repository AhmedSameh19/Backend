# PgBouncer (production)

This repo includes a minimal PgBouncer + API compose file at `docker-compose.prod.yml`.

## Files

- `.env.pgbouncer` (not committed): DigitalOcean Postgres connection details and PgBouncer tuning.
- `.env.pgbouncer.example`: template for `.env.pgbouncer`.
- `docker-compose.prod.yml`: runs `pgbouncer` + `api`.
- `infra/pgbouncer/pgbouncer.ini`: optional manual config example (not used by default).

## Notes

- PgBouncer runs on port `6432` on the host, and `5432` inside the Docker network.
- The API connects to PgBouncer (no TLS needed inside Docker); PgBouncer connects to DO Postgres with `sslmode=require`.
- If you run Celery workers that talk to Postgres, they should also connect via PgBouncer.

## Sizing for DO `max_connections = 25`

If **API + Celery** share the same DigitalOcean Postgres (and everything goes through PgBouncer), PgBouncer is what controls how many *server-side* connections hit Postgres.

Recommended starting point:

- `DEFAULT_POOL_SIZE=20`
- `RESERVE_POOL_SIZE=0`

That keeps Postgres usage under 25 and leaves headroom for migrations/admin connections.
If you also have other services connecting directly to Postgres, reduce `DEFAULT_POOL_SIZE` accordingly.


## Important: `DATABASE_URL` formats

- PgBouncer container expects a libpq URL like: `postgres://user:pass@host:port/dbname`
- The API uses SQLAlchemy and connects to PgBouncer via: `postgresql+psycopg://user:pass@pgbouncer:5432/dbname`

TLS to DigitalOcean Postgres is enforced via `SERVER_TLS_SSLMODE=require`.

Note: This repo previously referenced `PGBOUNCER_*` env vars for pool sizing; prefer the non-prefixed vars used by `edoburu/pgbouncer`.
