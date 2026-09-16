# LeadGen · n8n Control UI (optional)

A small, **standalone** Next.js 15 + React 19 app with its own dark theme
(deliberately different from the main product). It POSTs `{ category, location }`
to the `leadgen-webhook` n8n workflow and renders the returned leads.

This app is optional and **not part of the repository CI**. It talks only to the
n8n webhook — it does not call the Django API directly.

## Prerequisites

1. Import and **activate** `n8n/workflows/leadgen-webhook.json` in n8n.
2. Copy the *Webhook* node's **Production URL** (e.g.
   `http://localhost:5678/webhook/leadgen`).

## Run

```bash
cd n8n/ui
cp .env.example .env.local          # paste your webhook URL
npm install
npm run dev                         # http://localhost:3000
```

Build a static bundle:

```bash
npm run build                       # output in ./out
```

## Configuration

| Variable | Purpose |
| --- | --- |
| `NEXT_PUBLIC_N8N_WEBHOOK_URL` | Production URL of the `leadgen-webhook` workflow's Webhook node |

## Notes

- CORS: if the browser blocks the request, enable a permissive CORS response on
  the n8n webhook (n8n → Webhook node → *Response Headers*), or run the UI and
  n8n behind the same origin/proxy.
- This is a starter you can restyle or extend; it intentionally shares no code
  with `leadgen-frontend/`.
