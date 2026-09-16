# Developer Onboarding

## Prerequisites

- Python 3.10+
- Node.js 20
- Docker Desktop
- Firebase project with web app credentials

## Run the whole stack with Docker (fastest)

```bash
cp backend/.env.example backend/.env
cp leadgen-frontend/.env.example leadgen-frontend/.env
docker compose up --build -d
docker compose exec backend python manage.py migrate
```

Frontend at http://localhost:5173, API at http://localhost:8000/api/health/.
Container/topology details: [infrastructure.md](infrastructure.md). Prefer local
processes for active development? Continue below.

## Backend Setup

```bash
cd backend
cp .env.example .env
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

For local synchronous lead generation, keep:

```env
DEBUG=True
LEADGEN_SYNC_REQUESTS=True
```

Production should use Celery-backed async generation:

```env
DEBUG=False
LEADGEN_SYNC_REQUESTS=False
```

## Frontend Setup

The frontend is a **Next.js (App Router) + React 19** app, built as a static
export. Environment variables use the `NEXT_PUBLIC_` prefix.

```bash
cd leadgen-frontend
cp .env.example .env.local
npm install
npm run dev        # next dev  -> http://localhost:3000
```

Other commands:

```bash
npm run build      # next build -> static export in ./out
npm run lint       # eslint
npm test           # vitest (jsdom) with coverage
```

Routes: `/` (auth-aware redirect), `/login`, `/dashboard`. Route guards live in
`src/components/AuthGate.jsx`; screens are in `src/views`, shared UI in
`src/components`.

## Daily Workflow

Before opening a PR:

```bash
cd backend
pytest
pylint leadgen leads

cd ../leadgen-frontend
npm run lint
npm test
npm run build
```

## Authentication Flow

The frontend signs in with Firebase, then exchanges the Firebase ID token for a
Django SimpleJWT pair (`POST /api/token/firebase/`). Subsequent API requests use
the Django access token; the client auto-refreshes on 401. Either token is
accepted on:

```text
Authorization: Bearer <jwt-or-firebase-id-token>
```

See [security.md](security.md) for the full flow and token endpoints.
