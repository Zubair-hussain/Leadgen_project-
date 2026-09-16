# Operations

## Runtime Services

- Django API: `backend`
- Celery worker: `celery_worker`
- Celery beat: `celery_beat`
- PostgreSQL: `db`
- Redis: `redis`
- React static frontend: `frontend`

## Lead Generation

In development, `LEADGEN_SYNC_REQUESTS=True` keeps generation synchronous for easier debugging.

In production, set `LEADGEN_SYNC_REQUESTS=False`. The API returns a Celery task id and workers process generation outside the web request.

## Logs

Runtime logs must stay outside git. Use container logs or a centralized logging platform.

## Backups

Back up PostgreSQL volumes before schema migrations or production upgrades.
