# Infrastructure

The stack runs as five containers orchestrated by `docker-compose.yml` on a
private bridge network. Only the frontend and API are exposed (to localhost);
PostgreSQL and Redis stay internal.

![Infrastructure and deployment](diagrams/infrastructure.svg)

## Services

| Service | Image / build | Purpose | Host port |
| --- | --- | --- | --- |
| `frontend` | nginx + Next.js static export | Serves the built SPA | `127.0.0.1:5173 → 80` |
| `backend` | Python / gunicorn | Django REST API | `127.0.0.1:8000 → 8000` |
| `worker` | Python / celery | Async lead generation | — (internal) |
| `db` | postgres | Primary datastore | — (internal) |
| `redis` | redis | Celery broker + cache | — (internal) |

## Build-time vs run-time configuration

- **Frontend** (`NEXT_PUBLIC_*`) values are **baked at build time** into the
  static export, passed as Docker build args (see `docker-compose.yml` →
  `frontend.build.args` and the `Dockerfile` `ARG`/`ENV` block).
- **Backend** reads its configuration at **run time** from environment variables
  / `.env` (secrets, database, Redis, provider API keys).

## Networking & security

- All services share `leadgen_network`; `db` and `redis` are never published.
- Host bindings use `127.0.0.1` so nothing is exposed on the public interface
  without an explicit reverse proxy.
- The API sits behind an HTTPS-terminating reverse proxy in production; secure
  cookies + HSTS apply once TLS is stable. See [security.md](security.md).

## Common commands

```bash
# Build & start the whole stack
docker compose up --build -d

# Tail logs
docker compose logs -f backend worker

# Run backend migrations inside the container
docker compose exec backend python manage.py migrate

# Validate the compose file (also run in CI hygiene job)
docker compose config

# Stop everything
docker compose down
```

See [operations.md](operations.md) for runtime/Celery notes and
[onboarding.md](onboarding.md) for local (non-Docker) setup.
