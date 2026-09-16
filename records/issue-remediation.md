# Issue Remediation Register

## Security

- Django SimpleJWT integrated: `/api/token/`, `/token/refresh/`, `/token/verify/`,
  `/token/blacklist/`, and a `/token/firebase/` exchange endpoint. Refresh-token
  rotation with blacklist-after-rotation is enabled.
- A tolerant `FallthroughJWTAuthentication` lets Django JWTs and Firebase ID
  tokens share the `Bearer` header (dual auth) without one breaking the other.
- Frontend `api.js` now prefers the Django JWT, auto-refreshes on 401, and the
  login flow exchanges the Firebase session for a JWT pair; logout clears tokens.
- Missing `Lead` index migration (`0007`) generated so the DB schema matches the
  model; CI now fails on migration drift (`makemigrations --check`).
- Public API access replaced with authenticated defaults.
- Sensitive endpoints now use the global authenticated permission policy.
- Firebase ID tokens are attached by the frontend and verified by the backend.
- Leads now have an owner relation and user-scoped querysets.
- Public health response no longer leaks provider readiness or SMTP identity.
- `SECRET_KEY` no longer has a production fallback.
- Production security settings were added for SSL redirects, secure cookies, HSTS, content sniffing, frames, and referrer policy.
- Runtime files and environment files were removed from git and added to `.gitignore`.
- PostgreSQL and Redis are no longer published to the host by default.
- SSRF protections were added for page crawling.

## Performance

- CSV export is streamed instead of base64-encoding the full file in memory.
- DNS MX lookups are cached by domain.
- DKIM lookup duplication was reduced.
- Lead generation can run through Celery instead of blocking production web requests.
- Lead persistence now deduplicates in memory and uses `get_or_create`.

## Correctness

- Missing `re` import in file verification was fixed.
- File verification now enforces an upload size limit.
- Export and delete endpoints are scoped to the authenticated owner.
- Frontend export and sign-out buttons are wired.
- Frontend verification tab uses backend verification instead of random simulated results.
- Invalid URL rendering in the modular leads table is guarded.
- Fixed a `NameError` in `leads/views.py`: the CSV download path used `StringIO` and `base64` without importing them, so the generate endpoint returned HTTP 500. Both imports were added.
- Removed a dead, misspelled duplicate component directory (`leadgen-frontend/src/componet/`) that shadowed `components/` and skewed coverage.
- Guarded impure `Date.now()` call during render in `LeadsTable.jsx`.

## Engineering Practice

- Backend pytest, coverage, and pylint configuration added.
- Frontend vitest, coverage, and ESLint rules added.
- CI workflows added for backend, frontend, Docker Compose validation, and repository hygiene.
- Developer onboarding, testing, security, and operations docs added.
- Test suites completed to the ~80% coverage target on both stacks (backend pytest, frontend vitest), including a full integration test for the `Dashboard` page monolith.
- `eslint-plugin-react` added with `jsx-uses-vars`/`jsx-uses-react` so identifiers used only inside JSX (e.g. `<motion.div>`, dynamic icon components) are no longer false-flagged as unused; a test-file override supplies Node globals.
- Coverage provider switched to `istanbul` and `jsdom` added so the frontend suite runs from a clean install.
- Frontend migrated from Vite SPA to **Next.js 15 (App Router) + React 19**, built
  as a static export: `src/app/` routes with an `AuthGate` client guard, screens
  moved to `src/views/`, `VITE_*` env renamed to `NEXT_PUBLIC_*`, Firebase init
  guarded to the browser, Vitest kept via `vitest.config.js`, and Docker/nginx
  updated to serve the export. Tests, lint, coverage, and `next build` all green.
