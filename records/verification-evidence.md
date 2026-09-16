# Verification Evidence

## Commands Added To CI

```bash
python -m compileall -q .
python manage.py check --deploy
pylint leadgen leads
pytest
npm run lint
npm test
npm run build
docker compose config
```

## Verified Local Run (2026-09-16)

All gates were executed locally from a clean dependency install and pass.

### Backend (`backend/`, Python 3.10)

- `pytest` — **38 passed**, total coverage **83.4%** (fails under 80% via `--cov-fail-under=80`).
- `pylint leads leadgen` — rated **10.00/10**.
- `manage.py makemigrations --check --dry-run` — **No changes detected** (schema matches models).

### Frontend (`leadgen-frontend/`, Node 20)

- Stack: **Next.js 15 (App Router) + React 19**, static export.
- `npm test` (`vitest run --coverage`) — **87 passed**. Coverage: statements 84.7%, branches 80.2%, functions 82.0%, lines 88.4% (thresholds 80/70/80/80 enforced in `vitest.config.js`).
- `npm run lint` — **0 errors** (3 informational `no-console` warnings in the Dashboard debug logs).
- `npm run build` — `next build` static export to `out/` succeeds (routes `/`, `/login`, `/dashboard`).

### Security (JWT)

- Django SimpleJWT endpoints, refresh rotation + blacklist, and a Firebase→JWT
  exchange are covered by `backend/leads/tests/test_jwt.py`.
- Frontend token store, JWT-preferring interceptor, 401 auto-refresh, and the
  login exchange are covered by `src/services/api.test.jsx` and `Login.test.jsx`.

### Repository hygiene

- No runtime artifacts (`__pycache__`, `*.pyc`, `*.log`, `.env`, `credentials.json`) remain tracked.

## Notes

- The Vitest text reporter omits some 100%-covered files from its console table on this Windows path; the totals above (and `coverage/lcov.info`) still account for them.
