# Contributing to LeadGen AI

Thanks for your interest in contributing! This guide covers local setup, the
quality gates your change must pass, and the PR workflow.

## Prerequisites

- Python 3.10+
- Node.js 20 (see `.nvmrc`)
- Docker Desktop (optional, for the full stack)

## Getting started

```bash
# Backend
cd backend
cp .env.example .env
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

# Frontend
cd ../leadgen-frontend
cp .env.example .env.local
npm install
npm run dev
```

Full setup notes: [docs/onboarding.md](docs/onboarding.md).

## Quality gates (run before opening a PR)

Your change must keep all of these green — CI enforces them.

```bash
# Backend
cd backend
pytest                                   # tests + coverage (fails under 80%)
pylint leads leadgen                     # must stay at 10.00/10
python manage.py makemigrations --check --dry-run   # no model/migration drift

# Frontend
cd ../leadgen-frontend
npm run lint                             # ESLint, 0 errors
npm test                                 # Vitest + coverage
npm run build                            # next build (static export)
```

### Coverage configuration

- **Backend** — configured in `backend/pytest.ini` (`--cov-fail-under=80`) and
  `backend/.coveragerc` (omit rules). Add tests under `backend/leads/tests/`.
- **Frontend** — configured in `leadgen-frontend/vitest.config.js`
  (`thresholds`: statements 80, branches 70, functions 80, lines 80; `istanbul`
  provider). Colocate tests as `*.test.jsx` next to the file under test.

If you add code, add tests. If a threshold blocks you, raise coverage rather than
lowering the gate.

## Code style

- **Python:** keep pylint at 10/10; match the surrounding style. No unused
  imports, no bare `except`, keep functions focused.
- **JS/JSX:** ESLint must pass. React components used only in JSX are fine
  (`jsx-uses-vars` is enabled). Avoid `console.log` (use `console.warn/error`).
- Editor defaults are in `.editorconfig` (LF line endings, 2-space JS / 4-space
  Python indentation).

## Commits & pull requests

1. Branch from `main`: `feat/…`, `fix/…`, `docs/…`, `chore/…`.
2. Keep commits focused; write imperative subject lines
   (`Add JWT refresh retry`, not `added stuff`).
3. Don't commit secrets or runtime artifacts — `.env`, `*.log`, `__pycache__`,
   `credentials.json` are git-ignored and the hygiene CI check rejects them.
4. Update docs when behavior changes; regenerate the evidence pack if you touch
   the test suites (see [evidences/README.md](evidences/README.md)).
5. Open a PR describing what and why; ensure CI is green.

## Project layout

See the *Project structure* section of the [README](README.md). Key areas:
`backend/leads/` (API), `leadgen-frontend/src/` (UI), `docs/` (documentation),
`n8n/` (automation), `evidences/` (captured gate results).

## License

By contributing, you agree that your contributions are licensed under the
project's [MIT License](LICENSE).
