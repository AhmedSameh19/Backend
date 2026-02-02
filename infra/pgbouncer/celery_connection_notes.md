# Celery + PgBouncer (same Postgres)

If Celery workers use the same Postgres as the API, and you run PgBouncer in front of Postgres, you should also point Celery's database access at PgBouncer.

## Key rule

- **Do not let API and Celery connect directly to Postgres** when `max_connections` is low.
- Make *all* Postgres traffic go through PgBouncer so PgBouncer controls the server-side connection count.

## Practical limits

- DigitalOcean: `max_connections = 25`
- Recommended PgBouncer start: `PGBOUNCER_DEFAULT_POOL_SIZE = 20`, `PGBOUNCER_RESERVE_POOL_SIZE = 0`
- Leave headroom for migrations/admin connections.

## If your Celery code uses SQLAlchemy

Ensure workers inherit the same `DATABASE_URL` that points to PgBouncer.
Also consider setting `DB_POOL_SIZE` lower for workers if they are many processes.

Example guidance:
- API: `WEB_CONCURRENCY=4`, `DB_POOL_SIZE=50` (clients to PgBouncer)
- Celery workers: keep concurrency modest (e.g. 2-4 per machine)

Why: each worker process can create its own pool; PgBouncer will cap server connections, but too many client connections will increase queueing/latency.
