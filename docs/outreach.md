# Outreach setup

> **Sending from hello@zubairhussain.xyz with Resend, the daily autopilot and the Sunday report:** see [resend-autopilot-setup.md](resend-autopilot-setup.md).

The Outreach tab lets you draft a personal email to a verified lead, approve it,
and have it sent from **zubair@zubairhussain.xyz** (your Hostinger mailbox, over SMTP)
within safe limits. Nothing is sent without your approval, and **dry-run mode is on
by default**: nothing is sent until you set `OUTREACH_DRY_RUN=False`.

Go-live steps for Hostinger and the Oracle server are at the bottom:
[Hostinger mailbox](#a-hostinger-mailbox-one-time), [Oracle server](#b-oracle-server-247).

## How a message flows

```
Draft ──approve──▶ safety checks ──▶ Queued ──(every minute, by priority)──▶ checks again ──▶ SMTP ──▶ Sent
                         │                                   │                                       │
                         └─ blocked: reasons shown           └─ Skipped (suppressed, replied…)       ▼
                                                                         Inbox watch (every 5 min) ──▶ reply? stop
                                                                         no reply after 3 / 7 / 14 days ──▶ follow-up
```

## The cold email playbook (`outreach/playbook.py`)

The algorithm is built on what the Cold Email Hall of Fame (coldemails.world, from the
@SidHaldar_ post) shows about emails that got answers from busy founders: about five
sentences, written like one person to another, opening with the reader instead of the
sender, one easy ask, a short curious subject, and polite follow-ups.

**1. Every draft gets a score from 0 to 100** and a list of what to fix:

| Rule | Penalty |
| --- | --- |
| Over 120 words / under 30 words | -20 / -15 |
| More than 6 sentences (more than 8) | -10 (-20) |
| No question to answer / more than 2 questions | -15 / -10 |
| First sentence starts with "I", "I'm", "My name is" | -10 |
| "I/my" used much more than "you/your" | -10 |
| Subject over 8 words / Subject In Title Case | -10 / -5 |
| No mention of their name, trade or town | -15 |
| More than one link | -5 |

The Gemini writer is told the playbook shape (them → you in one line → one idea → one question)
and retries, up to 3 times, until the draft scores at least `OUTREACH_MIN_PLAYBOOK_SCORE` (70)
*and* passes the humanizer. The batch review email shows each draft's score and its top fix.
Auto-send never sends a draft below the score.

**2. Priority decides who is emailed first** when the queue holds more than today's limit:
follow-ups first (so a conversation keeps its timing), then businesses with **no website**
(+30, your best prospects), rating 4+ (+10), 20+ reviews (+5), then better-written emails.
Personal mailboxes (gmail.com and similar) go last.

**3. Warm-up.** A new mailbox that suddenly sends 30 cold emails a day looks like a spammer.
The daily limit starts at `OUTREACH_WARMUP_START` (5) on the first real send and rises by
`OUTREACH_WARMUP_STEP` (2) each day until `OUTREACH_DAILY_LIMIT`. The dashboard shows
"Sent today 3 / 7 (warming up to 30)".

**4. Follow-ups.** `OUTREACH_FOLLOWUP_DAYS=3,4,7` means: 3 days after the first email, then
4 days after that, then 7 days after that (day 3, 7, 14). They are short, plain, threaded as
replies (`Re:` + `In-Reply-To`, so they land under your first email) and end with a polite
"I'll leave it here" note. The sequence stops on any reply, bounce or opt-out, and a follow-up
is only created after the previous email in the thread really went out.

**5. Inbox watch (`outreach/inbox.py`).** Every `OUTREACH_INBOX_SYNC_SECONDS` (300), and always
right before follow-ups are scheduled, the mailbox is read over IMAP (read-only, nothing is marked
read). A reply marks the thread replied and cancels its follow-ups; out-of-office replies are ignored.
"unsubscribe", "remove me", "not interested" and similar suppress the address. Bounces from
mailer-daemon suppress the address that bounced. Every sent email is also saved to your Sent
folder, so Hostinger webmail shows the whole conversation.

## Branded email (`outreach/branding.py`)

Each email goes out as plain text **plus** an HTML version. The body stays a personal letter
(no banners, images or tracking pixels, which hurt delivery and look like marketing). The brand
is the signature: your **ZH.** mark (Instrument Serif, red full stop `#C8141E`) on the black card
from zubairhussain.xyz, with your name, `OUTREACH_SENDER_TITLE` and portfolio link. Then the
opt-out line. Preview it without sending anything:

```bash
python manage.py preview_outreach_email --out preview.html
```

Turn HTML off with `OUTREACH_HTML_EMAIL=False` (plain text with a text signature).

Safety checks (on approve **and** again just before sending):

- valid address syntax; lead must be **verified** (or, for a typed address, the domain must have MX records)
- not on the do-not-contact (suppression) list
- not already emailed in the last `OUTREACH_RECONTACT_DAYS` days, and not already queued
  (earlier emails in the same follow-up thread don't count)
- subject does not start with `Re:` / `Fwd:` (except a real follow-up); at most `OUTREACH_MAX_LINKS` links
- for a follow-up: the lead has not replied and the first email did not bounce

Sending limits:

- at most **one email per tick**, with a random **3–8 minute** gap between sends
- `OUTREACH_HOURLY_LIMIT` (5) and the warm-up daily limit (up to `OUTREACH_DAILY_LIMIT`)
- only between `OUTREACH_SEND_HOUR_START`–`OUTREACH_SEND_HOUR_END` (9–17) in `TIME_ZONE`, weekdays only

Every email gets an opt-out line plus a `List-Unsubscribe` header.

## Review emails (every draft)

Every new draft, however it is created, emails `OUTREACH_NOTIFY_EMAIL` (defaults to the
sending account) with the full text, any check failures, and a review link:

```
http://localhost:8000/api/outreach/review/<signed-token>/
```

The link opens a page where you can edit the subject and body, then **Approve and queue**,
**Save changes**, or **Reject**. Links are signed, expire after `OUTREACH_REVIEW_LINK_DAYS`
(7), and only work on the PC running LeadGen. Set `OUTREACH_NOTIFY_ON_DRAFT=False` to turn
the emails off.

## Humanizer check

`outreach/humanizer.py` encodes the humanizer skill's rules (Wikipedia's "Signs of AI
writing") plus cold-email spam signals.

- **Blocks approval** (with `OUTREACH_HUMANIZER_STRICT=True`): dashes, "not X but Y" contrasts,
  staged openers ("let's dive in"), chatbot phrases ("I hope this email finds you well"),
  deep-sounding sayings, arguing with no one, fake urgency, emojis, ALL CAPS, `!!`.
- **Warns only:** overused AI words (robust, seamless, elevate…), sales language, inflated
  significance, "serves as", curly quotes, several exclamation marks.

URLs are ignored by the check. Set `OUTREACH_HUMANIZER_STRICT=False` to turn the blocks into warnings.

## Batch review: one email, one approval

Drafts are no longer reviewed one by one. After `OUTREACH_BATCH_QUIET_SECONDS` (120) without a
new draft, every un-batched draft goes into **one batch** and you get **one email** listing them all
with a single review page: untick any email to drop it, edit any subject or body, then
**Approve all ticked** or **Reject whole batch**. Duplicate drafts for the same address are cancelled
automatically. `POST /api/outreach/batches/` creates a batch immediately.

## Auto-send when you don't answer

With `OUTREACH_AUTO_SEND_ENABLED=True`, a batch you have not decided within
`OUTREACH_AUTO_SEND_AFTER_HOURS` (12) is processed by the auto-send policy. **An email is queued only
when every check is certain; anything else stays a draft and you are told why.**

- all safety checks pass (verified lead, not suppressed, not recently contacted, no duplicates)
- the humanizer finds nothing at all (no warnings either)
- the address is a business domain (personal mailboxes such as gmail.com and outlook.com are never auto-sent)
- the email is within the word limit
- Gemini reviews it and answers "approve" with confidence of at least `OUTREACH_AUTO_SEND_MIN_CONFIDENCE`
  (0.9) and raises no concerns. If Gemini is down, unconfigured, unsure or unreadable, the email is held.
- you must have actually been notified: a batch whose review email failed is never auto-sent

Auto-sent emails still obey the daily and hourly limits, the send window and the dry-run switch.
After the policy runs you get a second email listing what was queued and what was held.

## SerpAPI business check

Before an email is written or sent, `outreach/research.py` looks the business up on Google Maps through
SerpAPI (name, rating, reviews, website, open or closed). Results are cached for
`OUTREACH_RESEARCH_MAX_AGE_DAYS` (3), then refreshed automatically, so new details are picked up. It is
used in four places:

1. **Gemini writer:** gets the real facts (business name, rating, whether they already have a website)
   and may mention one, exactly as given. A closed business is skipped.
2. **Review email:** each email in the batch shows the SerpAPI line (name, stars, website).
3. **Just before sending:** a business that now shows as permanently or temporarily closed is skipped,
   even if you approved it. A failed lookup does not block an email you approved yourself.
4. **Auto-send policy:** an email that no person approved is only sent with a confirmed Google Maps match.

Each refresh is one SerpAPI search. `OUTREACH_RESEARCH_DAILY_MAX` (50) caps refreshes per day to protect
your credits. Set `OUTREACH_RESEARCH_ENABLED=False` to turn the whole check off.

## Gemini

`GEMINI_API_KEY` and `GEMINI_MODEL` (default `gemini-3.8-flash`) power three things: the safety
reviewer above, the lead filter during lead generation, and `POST /api/outreach/ai-drafts/`, which
writes drafts for verified leads without one. Writer output must pass the humanizer check, otherwise the
lead is skipped. Drafts are never sent by the writer; they join the next batch.

## A. Hostinger mailbox (one time)

You need a Hostinger email plan on zubairhussain.xyz (the free mailbox that comes with
hosting, or Business Email).

1. **Create the mailbox.** hPanel → **Emails** → pick `zubairhussain.xyz` → **Email accounts** →
   create `zubair@zubairhussain.xyz` with a long, unique password. If it already exists, keep it.
2. **Note the server settings** (hPanel → Emails → your mailbox → **Connect apps & devices** →
   manual configuration). They should be:

   | | Host | Port | Security |
   | --- | --- | --- | --- |
   | Outgoing (SMTP) | `smtp.hostinger.com` | `465` | SSL |
   | Incoming (IMAP) | `imap.hostinger.com` | `993` | SSL |

3. **Deliverability DNS records.** hPanel → Emails → **DNS settings / Email deliverability** shows
   MX, SPF, DKIM and DMARC with a status. If the domain's DNS is at Hostinger, press the
   **Connect / Fix** button and Hostinger adds them. If the DNS is somewhere else (for example
   where your portfolio site's DNS lives), copy the records hPanel shows into that DNS provider.
   They look like this, but always use the exact values hPanel gives you:

   | Type | Name | Value |
   | --- | --- | --- |
   | MX | `@` | `mx1.hostinger.com` (priority 5), `mx2.hostinger.com` (priority 10) |
   | TXT (SPF) | `@` | `v=spf1 include:_spf.mail.hostinger.com ~all` |
   | CNAME (DKIM) | `hostingermail-a._domainkey` (and `-b`, `-c`) | the targets hPanel lists |
   | TXT (DMARC) | `_dmarc` | `v=DMARC1; p=none; rua=mailto:zubair@zubairhussain.xyz` |

   A domain can only have **one** SPF record: if one exists already, add
   `include:_spf.mail.hostinger.com` to it instead of creating a second. Without SPF and DKIM,
   most cold emails go straight to spam. DNS can take a few hours to update.
4. **Check your plan's daily sending limit** in hPanel and keep `OUTREACH_DAILY_LIMIT` far
   below it (30 is a sensible ceiling for one-to-one cold email from one mailbox). Hostinger's
   rules forbid bulk unsolicited mail; small, personal, well-targeted volume with an opt-out is
   what this system is built for. Going over that risks the mailbox being suspended.
5. **Webmail signature (optional).** So emails you write by hand in Hostinger webmail carry the
   same ZH. card: open `docs/hostinger-signature.html` in a browser, select all of the card, copy,
   then in Hostinger webmail → **Settings → Identities / Signatures** → paste it into the
   signature editor and save. LeadGen's own emails already include the card, and SMTP sends
   exactly what LeadGen builds, so they never get it twice. Regenerate the file any time with
   `python manage.py preview_outreach_email --signature-only --out ../docs/hostinger-signature.html`.
6. **Fill in `backend/.env`** (copy from `.env.example`):

   ```
   OUTREACH_TRANSPORT=smtp
   OUTREACH_FROM_EMAIL=zubair@zubairhussain.xyz
   OUTREACH_FROM_NAME=Zubair Hussain
   OUTREACH_SMTP_PASSWORD=<the mailbox password>
   OUTREACH_PORTFOLIO_URL=https://zubairhussain.xyz
   OUTREACH_DRY_RUN=True
   TIME_ZONE=Europe/London        # where your LEADS are, so 9-17 is their business day
   ```

   IMAP uses the same login automatically. Never commit `.env`.
7. **Test the mailbox** (logs in to SMTP and IMAP, finds the Sent folder, emails you a branded sample):

   ```bash
   docker compose exec backend python manage.py check_mailbox --send-test
   ```

   Open the sample on your phone and computer. For a deliverability score, go to
   <https://www.mail-tester.com>, copy the address it shows, and run
   `python manage.py check_mailbox --to <that address>`. Aim for 9/10 or better before going live;
   it tells you exactly which DNS record is missing.

## B. Oracle server (24/7)

An **Always Free Ampere A1** VM (2 to 4 OCPU, 12 to 24 GB RAM, Ubuntu 22.04 or 24.04) runs the
whole stack comfortably. The 1 GB AMD micro shape is too small for Postgres + Redis + Celery.

1. **Create the VM** (OCI Console → Compute → Instances → Create, image Ubuntu, shape VM.Standard.A1.Flex),
   download the SSH key, and note the public IP.
2. **Outbound mail:** Oracle blocks outbound port **25** on new tenancies. This setup uses **465**
   (SMTP) and **993** (IMAP), which are allowed, so there is nothing to request.
3. **Install Docker** on the VM:

   ```bash
   sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
   sudo systemctl enable --now docker
   sudo usermod -aG docker $USER   # log out and back in after this
   ```

4. **Copy the project and `.env`**, then start everything:

   ```bash
   git clone <your repo> leadgen && cd leadgen
   nano backend/.env   # DEBUG=False, a new SECRET_KEY, and the OUTREACH_* values from step A6
   docker compose up -d --build
   docker compose ps   # db, redis, backend, celery_worker, celery_beat should be running/healthy
   ```

   Every service has `restart: unless-stopped` and Docker starts on boot, so after a reboot or crash
   it all comes back by itself. `celery_beat` runs the send queue and batches every minute and the
   inbox watch + follow-ups every 5 minutes.
5. **Review links from your phone (recommended).** Review emails link to
   `OUTREACH_REVIEW_BASE_URL`. To open them anywhere, give the server a name and HTTPS:
   - DNS: an **A record** `leadgen` → the VM's public IP.
   - OCI: VCN → Security List → add ingress TCP **80** and **443** from `0.0.0.0/0`. Ubuntu images on
     Oracle also block them in iptables:
     `sudo iptables -I INPUT 6 -p tcp -m multiport --dports 80,443 -j ACCEPT && sudo netfilter-persistent save`
   - Caddy gives free automatic HTTPS: `sudo apt install -y caddy`, put this in `/etc/caddy/Caddyfile`,
     then `sudo systemctl reload caddy`:

     ```
     leadgen.zubairhussain.xyz {
         reverse_proxy 127.0.0.1:8000
     }
     ```

   - In `backend/.env`, then `docker compose up -d`:

     ```
     ALLOWED_HOSTS=leadgen.zubairhussain.xyz,localhost,127.0.0.1,backend
     CSRF_TRUSTED_ORIGINS=https://leadgen.zubairhussain.xyz
     USE_X_FORWARDED_PROTO=True
     OUTREACH_REVIEW_BASE_URL=https://leadgen.zubairhussain.xyz
     ```

6. **Watch it work:**

   ```bash
   docker compose logs -f celery_beat celery_worker
   docker compose exec backend python manage.py process_outreach_queue   # one tick + full status
   ```

## C. Dry run, then go live

1. In the dashboard, create drafts (or **AI drafts**) and approve the batch from the review email.
2. Inside the send window they show **Sent (dry run)**. Nothing left the server.
3. Set `OUTREACH_DRY_RUN=False`, run `docker compose up -d`, and send the first real one **to yourself**
   (a lead row with another address of yours). Reply to it from that address: within 5 minutes the
   thread shows as replied and its follow-ups are cancelled. That proves the whole loop.
4. Then let it run. The warm-up keeps the first week small on purpose.

## Using Gmail instead (optional)

Set `OUTREACH_TRANSPORT=gmail`, then:

1. <https://console.cloud.google.com/> → new project → **APIs & Services → Library → Gmail API → Enable**.
2. **OAuth consent screen**: Workspace → **Internal**; personal @gmail.com → **External** + add yourself as a
   test user (refresh tokens then **expire after 7 days**).
3. **Credentials → OAuth client ID → Desktop app**; put the ID and secret in `GOOGLE_CLIENT_ID` /
   `GOOGLE_CLIENT_SECRET`, and set `OUTREACH_FROM_EMAIL` to that Gmail address.
4. On your PC (not in Docker): `python manage.py gmail_authorize --write-env`.
5. For the inbox watch, set `OUTREACH_IMAP_HOST=imap.gmail.com` and a Google **app password** in
   `OUTREACH_IMAP_PASSWORD`. Otherwise set `OUTREACH_INBOX_SYNC_ENABLED=False` and
   `OUTREACH_FOLLOWUPS_ENABLED=False`, since follow-ups must know about replies.

## Troubleshooting

| Status / message | Meaning |
| --- | --- |
| `smtp-not-configured` / `gmail-not-configured` | Mailbox password (or `GOOGLE_*`) missing while dry run is off |
| `SMTP login refused ... check the mailbox password` | Wrong password, or the mailbox is suspended in hPanel |
| `Recipient refused by the server` | The address does not exist; add it to suppressions |
| `Sent, but could not save a copy to the Sent folder` | Only a warning; set `OUTREACH_IMAP_SENT_FOLDER` to your folder name |
| Inbox sync `error: ...` | IMAP host/password wrong or blocked; follow-ups wait for the next good sync |
| `Token refresh failed ... invalid_grant` | Gmail only: refresh token expired; run `gmail_authorize` again |
| `outside-send-window` | Outside business hours in `TIME_ZONE` or a weekend; it sends next working morning |
| `waiting-for-delay` / `hourly-limit-reached` / `daily-limit-reached` | Working as intended (warm-up included) |
| Emails land in spam | Run mail-tester (step A7); almost always a missing SPF/DKIM record |

## Directories: Yelp, Nextdoor, True Local

Pick **Yelp**, **Nextdoor** or **True Local** in the generator (with a city or suburb). `leads/directories.py` finds businesses, looks up each one's own website on Google Maps (SerpAPI), and reads the public email from that website.

| Source | How businesses are found | Notes |
| --- | --- | --- |
| Yelp | Official Yelp Fusion API (`YELP_API_KEY`) | Without a key it falls back to Google search results |
| Nextdoor | Google results for `site:nextdoor.com/pages` | Nextdoor's pages are never fetched (login wall, no business API) |
| True Local (Australia) | Google results for `site:truelocal.com.au` | The site blocks bots with Cloudflare; this does not try to get around that |

Each business costs about one SerpAPI search; `DIRECTORY_MAX_PER_RUN` (15) caps a run. Scraping these sites directly would break their terms and get blocked, so it is deliberately not done.

## Daily volume

Each day gets a random target between `OUTREACH_DAILY_MIN` (10) and `OUTREACH_DAILY_LIMIT` (20), the same all day and never exceeded. While the mailbox warms up, the warm-up cap applies if it is lower.

## Regional rules (`outreach/compliance.py`)

Each lead gets a `country` (from its address, phone number or website domain). Before every send:

| Region | Enforced |
| --- | --- |
| US (CAN-SPAM) | Postal address and sender identity in the footer, working opt-out, honest subject |
| UK / EU (GDPR, PECR) | Business mailboxes only, "why you got this" line (legitimate interest), right to object, privacy link |
| Australia (Spam Act) | Business mailboxes only, sender identification, "published business address" line, unsubscribe |
| Germany, Austria | Blocked by default (`OUTREACH_BLOCKED_COUNTRIES`); B2B cold email needs prior consent |
| Unknown country | Not emailed (`OUTREACH_REQUIRE_REGION`) |

Emails go out in the **lead's** business hours (US Central, UK, Central Europe, Sydney), so Australian leads are emailed in the Australian morning. Opt-outs are suppressed immediately by the inbox watch. Set `OUTREACH_SENDER_ADDRESS` before going live. This is a technical safeguard, not legal advice: confirm the rules for your target countries with a lawyer.

## Oracle Always Free (Ampere A1, 12 GB RAM)

The 12 GB plan is the right size: Postgres, Redis, Django, Celery worker and beat use about 2.5 GB. Suggested `.env` for it: `GUNICORN_WORKERS=4`, `CELERY_CONCURRENCY=3`. Steps: section B above, then copy `deploy/Caddyfile` to `/etc/caddy/Caddyfile` with your hostnames. Keep ports 80/443 open only in the Security List, and never open 5432, 6379 or 8000 publicly (compose already binds them to localhost or the internal network).

## Security notes

- **Front-end code can never be fully hidden.** Anything the browser runs can be read in dev tools. The build ships minified bundles with no source maps and no console output, and nginx refuses `.map` files, but real protection is on the server: every API call needs a login token, JSON-only responses, rate limits, a secret `ADMIN_URL`, locked-down CSP and security headers, HTTPS only, no error details returned, and secrets only in `backend/.env` (never in the front end, never in git).
- Scrapers and the AI keys live only on the server, so nobody who opens the site can see or reuse them.
- Rotate `SECRET_KEY` and the mailbox password if the server is ever shared or the repo leaked.
