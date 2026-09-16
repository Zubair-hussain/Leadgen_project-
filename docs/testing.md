# Testing And Quality Gates

## Backend

```bash
cd backend
pytest
pylint leadgen leads
python manage.py check --deploy
```

Backend coverage is configured in `backend/pytest.ini` with an 80% threshold for
the Django project packages.

## Frontend

```bash
cd leadgen-frontend
npm run lint
npm test
npm run build
```

Frontend coverage thresholds are configured in `vitest.config.js` (statements 80,
branches 70, functions 80, lines 80) using the `istanbul` provider on `jsdom`.
Tests are colocated with their components as `*.test.jsx`, plus a full
integration test for the `Dashboard` view in `src/views/Dashboard.test.jsx` and
route-guard tests for `AuthGate` / `useAuthUser`.

## Current baseline

| Stack    | Suite            | Result                                   |
| -------- | ---------------- | ---------------------------------------- |
| Backend  | `pytest`         | 25 passed · 82.5% coverage               |
| Backend  | `pylint`         | 10.00/10                                 |
| Frontend | `vitest`         | 87 passed · 84.7% stmts / 88.4% lines    |
| Frontend | `eslint`         | 0 errors                                 |
| Frontend | `next build`     | static export to `out/` succeeds         |

Run a single frontend test file with `npx vitest run <path>`; open the HTML
coverage report from `leadgen-frontend/coverage/lcov-report/index.html`.

## CI

GitHub Actions run:

- Python compile check
- Django deploy check
- Pylint
- Pytest coverage
- ESLint
- Vitest coverage
- Vite build
- repository hygiene checks
