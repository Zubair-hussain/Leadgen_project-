# Frontend ↔ Backend Integration

> This early note has been superseded. The frontend is now a Next.js (App
> Router) + React 19 app, and auth uses Django SimpleJWT (exchanged from
> Firebase). See the canonical docs:

- [architecture.md](architecture.md) — system architecture, diagrams, data flow.
- [security.md](security.md) — authentication (JWT) flow and token endpoints.
- [onboarding.md](onboarding.md) — local setup and environment variables.
- [wireframes.md](wireframes.md) — screen-by-screen UX.

## Integration at a glance

- Frontend calls the API at `NEXT_PUBLIC_API_URL` (default
  `http://localhost:8000/api`).
- The health indicator polls `GET /api/health/`; see
  `src/components/ConnectionStatus.jsx`.
- Requests attach `Authorization: Bearer <token>` (Django JWT preferred, Firebase
  ID token as fallback) via `src/services/api.js`.
- CORS origins are configured in `backend/leadgen/settings.py`
  (`CORS_ALLOWED_ORIGINS`).

Environment variables are documented in `leadgen-frontend/.env.example` and
`backend/.env.example`; never commit real `.env` files.
