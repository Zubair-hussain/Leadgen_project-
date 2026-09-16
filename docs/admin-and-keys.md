# Admin & API Keys — complete reference

Everything you need to configure the project and open the admin panel. **No key
is ever stored in client code or committed** — provider keys live in the backend
env (or your host/Vercel env), and the admin password is set by you, hashed.

---

## 1. All API keys / environment variables

### Provider API keys (the "parents") — backend `backend/.env`

These power the lead **sources** and optional AI filtering. All are **optional**
(the app runs without them, with fewer sources) — set the ones you want.

| Key | Powers | Where to get it | Guide |
| --- | --- | --- | --- |
| `SERPAPI_KEY` | Google search + Maps (primary engine) | https://serpapi.com/manage-api-key | [blog](../blog/how-to-get-serpapi-key.html) |
| `APIFY_API_KEY` | Apify deep crawl / "Professional" mode; LinkedIn & Upwork actors | https://console.apify.com → Settings → Integrations → API tokens | [blog](../blog/how-to-get-apify-token.html) |
| `GOOGLE_API_KEY` | Google Programmable (Custom) Search | https://console.cloud.google.com → enable Custom Search API → API key | [blog](../blog/how-to-get-google-programmable-search.html) |
| `GOOGLE_CX` | Search-engine ID for the above | https://programmablesearchengine.google.com | same |
| `GEMINI_API_KEY` | Optional AI relevance filtering | https://aistudio.google.com → Get API key | [blog](../blog/how-to-get-gemini-api-key.html) |

### Backend core config — `backend/.env`

| Var | Purpose |
| --- | --- |
| `SECRET_KEY` | Django secret (also signs JWTs) — **required in production** |
| `DEBUG` | `True` locally, `False` in production |
| `ALLOWED_HOSTS` | Comma-separated hostnames |
| `CORS_ALLOWED_ORIGINS` | Comma-separated frontend origins |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_HOST` / `POSTGRES_PORT` | Database |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Redis for async jobs |
| `LEADGEN_SYNC_REQUESTS` | `True` = generate synchronously (dev); `False` = via Celery |
| `JWT_ACCESS_MINUTES` / `JWT_REFRESH_DAYS` | Token lifetimes (default 15 / 7) |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` / `DEFAULT_FROM_EMAIL` | Outbound email |

### Frontend (Next.js) — `leadgen-frontend/.env.local`

`NEXT_PUBLIC_*` values are **baked in at build time** (public by design — never put
secrets here).

| Var | Purpose |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | Base URL of the Django API (e.g. `http://localhost:8000/api`) |
| `NEXT_PUBLIC_FIREBASE_API_KEY` … `NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID` | Firebase web config (7 values, from the Firebase console → Project settings) |

### n8n control UI (optional) — `n8n/ui/.env.local`

| Var | Purpose |
| --- | --- |
| `NEXT_PUBLIC_N8N_WEBHOOK_URL` | Production URL of the `leadgen-webhook` workflow |

### CI / deploy (GitHub → Settings → Secrets and variables → Actions)

| Name | Type | Enables |
| --- | --- | --- |
| `VERCEL_TOKEN` | secret | Vercel deploy workflow |
| `VERCEL_ORG_ID` | secret | " |
| `VERCEL_PROJECT_ID` | secret | " |
| `SITE_URL` | variable | Tuesday Lighthouse audit |
| `SEO_DOMAIN` | variable | Semrush audit target |
| `SEMRUSH_API_KEY` | secret | Semrush audit |

> Provider keys go in `backend/.env` (or your host's env). For a deployed API on a
> platform with an env UI (Vercel/Render/Railway/Fly), paste them there instead of
> a file. The static landing page needs **none** of these.

---

## 2. How to open the admin panel

The admin is Django's built-in admin, protected by a password **you** set. There
is no secret hardcoded anywhere.

### Step 1 — create your admin account (once)

```bash
cd backend
python manage.py createsuperuser
```

Enter a username, email, and a strong password when prompted. (Docker:
`docker compose exec backend python manage.py createsuperuser`.)

### Step 2 — open the admin

Start the backend, then visit:

```
http://localhost:8000/admin/
```

Log in with the username + password from Step 1.

### Step 3 — what you can do there

- **Users** — view/edit accounts; toggle **Staff status** to grant or revoke
  *premium*.
- **Leads** — browse, filter, and delete stored leads.

### Premium (no lead-generation limit)

Any user with **`is_staff = True`** is premium and **bypasses the `5/5m`
generation rate limit** (regular users get HTTP `429` when they exceed it). To
make someone premium: Admin → Users → open the user → tick **Staff status** →
Save. (Enforced server-side in `GenerateLeadsView`.)

### Using premium from the API

```bash
# 1. Get a token as your admin user
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"<your-admin>","password":"<your-password>"}'

# 2. Call generate with the access token — no rate limit for staff
curl -X POST http://localhost:8000/api/generate/ \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d '{"category":"Dentists","platforms":["reddit","google-maps"],"target_location":"Austin"}'
```

### Security notes

- Never commit `.env` or real passwords — they're git-ignored and the CI hygiene
  check rejects them.
- The landing page's 3-run demo limit is client-side only; real limits/premium
  are enforced by the backend against the authenticated user.
- Rotating `SECRET_KEY` invalidates all issued JWTs (a fast way to force
  re-login everywhere).

See also: [security.md](security.md) · [onboarding.md](onboarding.md) ·
[the API-key blog guides](../blog/index.html).
