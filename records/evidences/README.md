# Evidence Pack

Captured outputs from the quality gates, for reviewers who want proof the
project builds, tests, and lints cleanly. Regenerate anytime with the commands
in each section (or `docs/testing.md`).

> Captured on 2026-09-16 from a clean local run (Python 3.10, Node 20).

## Backend (`evidences/backend/`)

| File | What it shows | Result |
| --- | --- | --- |
| `pytest-results.txt` | Full `pytest -v` run with coverage table | **38 passed** · **83.4%** |
| `coverage-summary.txt` | `coverage report` summary | ≥ 80% gate met |
| `coverage.cobertura.xml` | Machine-readable coverage (Cobertura) | — |
| `pylint.txt` | `pylint leads leadgen` | **10.00/10** |
| `migrations-check.txt` | `makemigrations --check --dry-run` | No drift |

## Frontend (`evidences/frontend/`)

| File | What it shows | Result |
| --- | --- | --- |
| `vitest-results.txt` | Full `vitest --coverage` verbose run | **87 passed** |
| `coverage/lcov.info` | Machine-readable coverage (lcov) | stmts 84.7% / lines 88.4% |
| `eslint.txt` | `npm run lint` | **0 errors** |
| `next-build.txt` | `next build` static export | routes `/`, `/login`, `/dashboard` |

## Logs (`evidences/logs/`)

| File | What it shows |
| --- | --- |
| `frontend-smoke.txt` | Static export served + HTTP 200 on all routes |
| `backend-check.txt` | `manage.py check` — no issues |
| `docker-compose-config.txt` | `docker compose config` validates |

> Logs use a `.txt` extension so they can be committed; the repository-hygiene
> CI check rejects tracked `*.log` files.

## How to regenerate

```bash
# Backend
cd backend
pytest                       # -> pytest-results / coverage
python -m coverage html -d ../evidences/backend/htmlcov
pylint leads leadgen

# Frontend
cd ../leadgen-frontend
npm test                     # -> vitest + coverage
npm run lint
npm run build
```
