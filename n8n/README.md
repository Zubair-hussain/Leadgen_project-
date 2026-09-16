# n8n Automation for LeadGen AI

This folder contains ready-to-import [n8n](https://n8n.io) workflows that automate
LeadGen AI by calling its **existing REST API** — no backend changes are required.
n8n is an external orchestrator: it authenticates against `/api/token/` and then
posts to `/api/generate/` on a schedule or on demand.

```
n8n/
├── workflows/
│   ├── leadgen-scheduled.json   # runs generation every 24h
│   └── leadgen-webhook.json     # generates on demand via a webhook (used by the optional UI)
└── ui/                          # OPTIONAL Next.js control panel (separate, dark theme)
```

> Nothing here is wired into the Django app automatically. The workflows are a
> convenience layer on top of the public API you already run.

## What the workflows do

Both workflows follow the same real API calls:

1. **Config** — an *Edit Fields* node holding `apiBase`, a Django `username` /
   `password`, and the target `category` / `location`. Edit these (or swap in n8n
   credentials).
2. **Get JWT** — `POST {apiBase}/token/` → returns `{ access, refresh }`.
3. **Generate Leads** — `POST {apiBase}/generate/` with
   `Authorization: Bearer <access>` and a JSON body
   (`category`, `niche`, `platforms`, `target_location`, `is_professional`).
4. Handle the response (`$json.leads`, `$json.csv_base64`).

- `leadgen-scheduled.json` runs on a 24-hour schedule and branches on whether any
  leads were returned. Add your own delivery step (Google Sheets, Slack, email,
  CRM) after the **Leads generated** node.
- `leadgen-webhook.json` exposes `POST /webhook/leadgen` that accepts
  `{ "category": "...", "location": "..." }` and responds with the generated
  leads. The optional UI in [`ui/`](ui) calls this.

## Set up n8n (free)

You can self-host n8n for free (it is [fair-code licensed](https://docs.n8n.io/sustainable-use-license/)).

**Docker (recommended):**

```bash
docker run -it --rm --name n8n -p 5678:5678 -v n8n_data:/home/node/.n8n docker.n8n.io/n8nio/n8n
```

**npm:**

```bash
npx n8n
```

Open http://localhost:5678 and create your local owner account.

> If LeadGen runs on your host and n8n runs in Docker, use
> `http://host.docker.internal:8000/api` as `apiBase` instead of `localhost`.

## Import a workflow

1. In n8n: **Workflows → Import from File**.
2. Choose `n8n/workflows/leadgen-scheduled.json` (or `leadgen-webhook.json`).
3. Open the **Config** node and set `apiBase`, `username`, `password`,
   `category`, `location`. Prefer n8n **credentials** over plain values for the
   password.
4. For the webhook workflow, **Activate** it and copy the **Production URL** of
   the *Webhook* node.
5. Run once with **Execute Workflow** to verify.

The Django `username` / `password` is a normal Django user. Create one with:

```bash
cd backend && python manage.py createsuperuser
```

## Getting the free-tier provider API keys

These keys power the backend's lead **sources**. They are **optional** — the app
runs without them, just with fewer sources (the backend prints
“Features without API keys will still work” on startup). Put the keys in
`backend/.env` (see `backend/.env.example`). Free tiers and quotas change over
time, so confirm current limits on each provider's pricing page.

### SerpAPI — `SERPAPI_KEY`
Powers Google search and Google Maps lookups.
1. Sign up at https://serpapi.com/users/sign_up
2. Copy your key from the **API Key** page (https://serpapi.com/manage-api-key).
3. Set `SERPAPI_KEY=...` in `backend/.env`.
SerpAPI offers a free plan with a limited number of searches per month.

### Google Programmable Search — `GOOGLE_API_KEY` + `GOOGLE_CX`
Powers the Google Custom Search source.
1. Create a **Programmable Search Engine** at
   https://programmablesearchengine.google.com/ → copy the **Search engine ID**
   into `GOOGLE_CX`.
2. In Google Cloud Console (https://console.cloud.google.com/), enable the
   **Custom Search API** and create an **API key** → set `GOOGLE_API_KEY`.
The Custom Search JSON API has a free daily query allowance.

### Apify — `APIFY_API_KEY`
Powers the “Professional” deep-crawl mode (Google Maps enrichment).
1. Sign up at https://console.apify.com/sign-up
2. Copy your token from **Settings → Integrations → API tokens**.
3. Set `APIFY_API_KEY=...`.
Apify's free plan includes a monthly platform credit.

### Google Gemini — `GEMINI_API_KEY`
Optional AI relevance-filtering of generated leads.
1. Open **Google AI Studio** at https://aistudio.google.com/
2. **Get API key** → create a key.
3. Set `GEMINI_API_KEY=...`.
Google AI Studio provides a free tier for the Gemini API.

> Firebase (Google sign-in) is separate from the above and is documented in the
> main [docs/onboarding.md](../docs/onboarding.md) and
> [docs/security.md](../docs/security.md).

## Optional: the n8n control UI

[`ui/`](ui) is a small, standalone **Next.js** app with its own dark theme
(intentionally different from the main product). It posts to the
`leadgen-webhook` workflow and lists the returned leads. It is optional and not
part of the CI pipeline. See [`ui/README.md`](ui/README.md).
