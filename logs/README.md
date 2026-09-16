# logs/

Scratch space for local runtime logs. Log files are **git-ignored** — only this
README and `.gitkeep` are tracked, so the folder exists on a fresh clone without
committing noisy or sensitive output.

## Where logs actually come from

- **Backend (Django/Celery):** by default the app logs to `backend/leadgen.log`
  (git-ignored). Point logging here instead by configuring `LOGGING` in
  `backend/leadgen/settings.py` if you prefer a single location.
- **Docker:** use `docker compose logs -f <service>` (e.g. `backend`, `worker`).
- **Frontend/n8n:** browser console and the n8n execution log, respectively.

## Committed evidence vs. runtime logs

Do not commit raw `*.log` files — the repository-hygiene CI check rejects them.
Curated proof-of-run output lives under [`../evidences/`](../evidences/README.md)
using `.txt` files instead.
