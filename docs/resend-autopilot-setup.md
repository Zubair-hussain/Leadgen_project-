# Resend + Autopilot + Sunday report: setup

This turns LeadGen into a hands-off loop:

```
07:00 PKT      find new leads (SerpAPI Google Maps) for today's target in your list
07:30 PKT on   Gemini drafts emails (2 per run, 6 a day) offering the ONE service that fits the lead:
               no website -> design & layout; has a website -> free security check or SEO check
               drafts are batched -> one review email to you -> approve, or auto-send after 3 hours
from 07:00     5 emails a day leave hello@zubairhussain.xyz via Resend, 3-8 min apart, between
(lead's time)  07:00 and 11:00 in the LEAD's own time zone (Austin 7am, Manchester 7am, Melbourne 7am)
instantly      replies stop follow-ups; bounces, spam reports and one-click unsubscribes are blocked forever
Sunday 18:00   you get "Weekly outreach report: N emails sent" in thezubairh@gmail.com
Sunday 08:00   watchdog: security, leaks, Lighthouse, new attacks, law-page changes (email only if needed)
every 15 min   watchdog: uptime (one email when down, one when back)
```

Why 07:00 in the lead's time and not 07:00 in Pakistan: 07:00 PKT is 21:00 the night before in Texas.
Emails that arrive at the top of the inbox when the owner starts the day get the most replies. If you
really want one clock for everyone, set `OUTREACH_SEND_TIMEZONE=Asia/Karachi`.

Do the steps in order. Steps 1 to 4 are what keep you out of the spam folder.

---

## 0. Unblock the backend in Vercel (do this first)

The watchdog found that `leadgen-backend-nu.vercel.app` answers automated calls with Vercel's bot
challenge (HTTP 403, `x-vercel-mitigated: challenge`). While that is on, the GitHub scheduler, the Resend
webhook and Gmail's one-click unsubscribe **cannot reach the app**, so nothing is sent automatically.

Vercel → backend project → **Firewall**: turn **Attack Challenge Mode** off, or add a custom rule
"Path starts with `/api/outreach/`" → **Bypass**. The cron endpoint is already protected by `CRON_SECRET`
and the webhook by its signature, so bypassing the challenge there is safe.

## 1. Verify the domain in Resend (DKIM + SPF)

1. resend.com → **Domains → Add domain** → `zubairhussain.xyz`.
2. Resend shows 3 records. Add them in **Cloudflare → DNS → Records**, all **DNS only (grey cloud)**:

   | Type | Name | Value |
   | --- | --- | --- |
   | TXT | `resend._domainkey` | the long `p=MIIB...` key Resend shows (DKIM) |
   | MX | `send` | `feedback-smtp.<region>.amazonses.com`, priority 10 |
   | TXT | `send` | `v=spf1 include:amazonses.com ~all` |

   These live on the `send` subdomain, so your **Hostinger MX and SPF on the root stay exactly as they are**. Do not add a second SPF record on `@`.
3. Click **Verify**. Wait until all three are green.
4. In the domain's settings in Resend, turn **Open tracking OFF** and **Click tracking OFF**. Tracking pixels and rewritten links are one of the biggest spam signals for cold email.

## 2. DMARC

You already have `_dmarc` = `v=DMARC1; p=none; rua=mailto:zubair@zubairhussain.xyz`. Keep `p=none` for the first 3 to 4 weeks. When the weekly reports show low bounces and no complaints, change it to:

```
v=DMARC1; p=quarantine; rua=mailto:zubair@zubairhussain.xyz; adkim=r; aspf=r
```

## 3. Make sure replies reach you

Resend only **sends**. People will reply to the address in `Reply-To`.

1. In **Hostinger hPanel → Emails**, create `hello@zubairhussain.xyz` as a **forwarder (alias) to `zubair@zubairhussain.xyz`**. Otherwise anyone replying straight to hello@ gets a bounce, which hurts you.
2. Set `OUTREACH_REPLY_TO=zubair@zubairhussain.xyz` (step 6). The app sets the `Reply-To` and the unsubscribe link to that mailbox.
3. Keep the IMAP settings pointing at `zubair@zubairhussain.xyz` on `imap.hostinger.com`. The app reads that inbox every 5 minutes, so a reply stops the follow-ups and "unsubscribe" adds them to the suppression list.

## 4. Bounce and complaint webhook

1. Resend → **Webhooks → Add endpoint**:
   `https://<your-backend>.vercel.app/api/outreach/webhooks/resend/`
2. Events: **email.bounced** and **email.complained**.
3. Copy the **signing secret** (`whsec_...`) into `RESEND_WEBHOOK_SECRET`.

Anything that bounces or marks you as spam is never emailed again, and their queued follow-ups are cancelled.

## 5. API key

Resend → **API Keys → Create** → permission **Sending access**, domain `zubairhussain.xyz`. Copy it to `RESEND_API_KEY`.

The free plan allows 100 emails per day and 3,000 per month. The warm-up limits below stay under that.

## 6. Environment variables (Vercel → backend project → Settings → Environment Variables)

`backend/.env.vercel` (git-ignored, on your PC) already holds all of this with your values: 5 emails a day,
07:00 Pakistan start, booking link, services. Fill the 4 `<FILL ...>` values (Resend key, webhook secret,
Hostinger mailbox password, postal address), then paste the whole file into Vercel. The block below
explains the main ones.

```env
# Sending
OUTREACH_TRANSPORT=resend
OUTREACH_FROM_EMAIL=hello@zubairhussain.xyz
OUTREACH_FROM_NAME=Zubair Hussain
OUTREACH_REPLY_TO=zubair@zubairhussain.xyz
RESEND_API_KEY=re_...
RESEND_WEBHOOK_SECRET=whsec_...
OUTREACH_SENDER_ADDRESS=<your postal address>   # legally required in every cold email
OUTREACH_PRIVACY_URL=https://zubairhussain.xyz/privacy

# Inbox watching (replies, opt-outs, bounces)
OUTREACH_IMAP_HOST=imap.hostinger.com
OUTREACH_IMAP_USER=zubair@zubairhussain.xyz
OUTREACH_IMAP_PASSWORD=<mailbox password>
OUTREACH_IMAP_SAVE_SENT=False
OUTREACH_INBOX_SYNC_ENABLED=True
OUTREACH_FOLLOWUPS_ENABLED=True

# Warm-up for a brand new domain: 5 on day one, +2 a day, never above 25
OUTREACH_WARMUP_ENABLED=True
OUTREACH_WARMUP_START=5
OUTREACH_WARMUP_STEP=2
OUTREACH_DAILY_MIN=10
OUTREACH_DAILY_LIMIT=25
OUTREACH_HOURLY_LIMIT=5

# Autopilot (find leads + draft)
OUTREACH_AUTOPILOT_ENABLED=True
OUTREACH_AUTOPILOT_OWNER=thezubairh@gmail.com     # the account you sign in with
OUTREACH_AUTOPILOT_TARGETS=dentists|Austin, TX; plumbers|Manchester, UK; cafes|Sydney, AU
OUTREACH_AUTOPILOT_PLATFORMS=google-maps
OUTREACH_AUTOPILOT_DRAFTS_PER_DAY=15

# Hands-off sending: after 12 h without your answer, drafts that pass EVERY check are sent
OUTREACH_AUTO_SEND_ENABLED=True
OUTREACH_AUTO_SEND_AFTER_HOURS=12
OUTREACH_REVIEW_BASE_URL=https://<your-backend>.vercel.app

# Sunday report to your Gmail
OUTREACH_NOTIFY_EMAIL=thezubairh@gmail.com
OUTREACH_WEEKLY_REPORT_ENABLED=True
OUTREACH_REPORT_TIMEZONE=Asia/Karachi
OUTREACH_REPORT_WEEKDAY=6        # 6 = Sunday
OUTREACH_REPORT_HOUR=18          # 6 pm

# Leave ON until step 8 passes
OUTREACH_DRY_RUN=True
```

Also needed (you probably have them already): `SERPAPI_KEY`, `GEMINI_API_KEY`, `CRON_SECRET`.

Targets format: `category|location`, separated by `;`. One target is used per day, rotating. Germany and Austria are blocked by default (they need prior consent), and UK/EU/AU leads with Gmail/Outlook addresses are skipped.

Redeploy the backend after saving the variables.

## 7. Scheduler (GitHub Actions)

The workflow `.github/workflows/cron.yml` already runs every 5 minutes and now also calls the autopilot every 30 minutes. In **GitHub → repo → Settings → Secrets and variables → Actions** make sure these exist:

- `BACKEND_URL` = `https://<your-backend>.vercel.app`
- `CRON_SECRET` = the same value as in Vercel

Run it once by hand: **Actions → Outreach scheduler → Run workflow**, and check the log shows JSON such as `{"queue": "...", "report": "not-due"}` and `{"autopilot": "hunted 12 new leads: dentists in Austin, TX"}`.

## 8. Test before going live

0. **Test email**: `python manage.py send_test_email` sends the exact branded email a lead gets to your
   Gmail. `python manage.py send_test_email --to <address from mail-tester.com>` gives a spam score.
1. **Report**: locally, `python manage.py send_weekly_report --print` shows the report; without `--print` it emails it to you now.
2. **Spam score**: send one real email to the address from [mail-tester.com](https://www.mail-tester.com) (add it as a lead or use the Outreach page). Aim for **9/10 or better**. It tells you if SPF, DKIM or DMARC is missing.
3. **Gmail check**: send one to yourself at Gmail, open it → ⋮ → **Show original**. You want `SPF: PASS`, `DKIM: PASS`, `DMARC: PASS`.
4. Set up **Google Postmaster Tools** (postmaster.google.com) for `zubairhussain.xyz` to watch spam rate from Gmail users. Keep it under 0.1%.

When all of that is fine, set `OUTREACH_DRY_RUN=False` and redeploy. You are live.

## 9. Habits that keep you in the inbox

- **Go slow for the first month.** The warm-up already does 5 → 25 a day. Do not raise `OUTREACH_DAILY_LIMIT` above 30 for a new domain.
- **During week one, also send some normal emails** from hello@ to friends or your own other accounts and reply to them. Real conversations build reputation.
- **Watch the Sunday report.** Bounce rate above 3% or any spam complaint → pause (`OUTREACH_AUTOPILOT_ENABLED=False`) and fix the leads or the wording.
- The app already enforces: max 2 links, no fake "Re:", short human-sounding emails, an unsubscribe header and line, your postal address, one email at a time with random 3 to 8 minute gaps, business hours only, no re-contact within 30 days.

## Troubleshooting

| Report / log says | Fix |
| --- | --- |
| `resend-not-configured` | `RESEND_API_KEY` or `OUTREACH_FROM_EMAIL` missing in Vercel |
| `Resend refused the email (403): ... domain is not verified` | finish step 1 |
| `owner-not-found` | `OUTREACH_AUTOPILOT_OWNER` must be your account's username or email |
| `no-new-leads-to-draft` | normal until the next daily hunt; or the target cities give no business emails, try others |
| `hunted 0 new leads` | check `SERPAPI_KEY` credits; try a bigger city or broader category |
| Report never arrives | `OUTREACH_NOTIFY_EMAIL` set? Check spam once and mark "Not spam". Check `OUTREACH_REPORT_TIMEZONE` |


## 10. Gmail / Yahoo / Outlook sender rules (what the app does for each)

| Rule (Gmail Feb 2024, Yahoo, Outlook May 2025) | How it is met |
| --- | --- |
| SPF and DKIM pass, aligned with the From domain | Resend DKIM on `zubairhussain.xyz`, SPF on `send.` (step 1) |
| DMARC record exists | `_dmarc` already set (step 2); watchdog alerts if it disappears |
| One-click unsubscribe (RFC 8058) | `List-Unsubscribe` https link + `List-Unsubscribe-Post`, plus a footer link |
| Honour unsubscribes within 2 days | instant: suppressed the moment they click or reply |
| Spam complaint rate under 0.3% (aim < 0.1%) | complaints suppressed by webhook; Sunday report shows them |
| Valid headers, TLS, real Message-ID | done by the app and Resend |
| No deceptive subject, no fake "Re:" | blocked by the content checks |

## 11. US vs EU / UK / Australia law (what the app does per lead)

| Region | Law | What happens |
| --- | --- | --- |
| US | CAN-SPAM | allowed without consent; footer says it is a business offer, shows your name and **postal address**, opt-out works for 30+ days |
| UK | PECR + UK GDPR | business addresses only (no gmail/outlook); footer says where the address came from, legitimate interest, right to object |
| EU | ePrivacy + GDPR | same as UK; **Germany and Austria blocked** (they need prior consent) |
| Australia | Spam Act 2003 | business addresses only, published-address notice, opt-out |
| Anywhere else (e.g. Canada CASL) | | **never emailed**: unknown regions are blocked |

This is enforced in code, not legal advice. The watchdog checks the FTC, ICO, EDPB, ACMA and
Gmail/Yahoo/Outlook pages every Sunday and emails you when their wording changes.

## 12. Watchdog setup (GitHub → Settings → Secrets and variables → Actions)

- Variable `WATCH_URLS` = `https://leadgen-backend-nu.vercel.app/,https://zubairhussain.xyz,https://calendly-booking-navy.vercel.app/` (add your dashboard URL too)
- Variable `EMAIL_DOMAIN` = `zubairhussain.xyz`
- Secret `RESEND_API_KEY` (same key) and secret `ALERT_EMAIL` = your Gmail
- Optional: secret `CLOUDFLARE_API_TOKEN` (a token with only *Zone Settings: Read*) and `CLOUDFLARE_ZONE_ID`

Without the Resend key the watchdog opens a GitHub issue instead, and GitHub emails you about it.
Run it by hand once: **Actions → Watchdog → Run workflow** (mode `weekly`).
