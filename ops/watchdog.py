"""Watchdog for LeadGen: uptime, leaks, security, email auth, Lighthouse, new attacks and law changes.

Runs in GitHub Actions (.github/workflows/watchdog.yml). Standard library only.

  python ops/watchdog.py uptime   every 15 min: are the sites up? Emails once when down, once when back.
  python ops/watchdog.py weekly   every Sunday: full check, emails a report only when something needs you.

Settings come from environment variables (GitHub secrets / variables):
  WATCH_URLS            comma list of public URLs (frontend, backend, portfolio, booking page)
  EMAIL_DOMAIN          zubairhussain.xyz (SPF / DKIM / DMARC checks)
  RESEND_API_KEY        to email you; without it a GitHub issue is opened instead (GitHub emails you)
  ALERT_EMAIL           where alerts go;  ALERT_FROM  e.g. "LeadGen Watchdog <hello@zubairhussain.xyz>"
  CLOUDFLARE_API_TOKEN  + CLOUDFLARE_ZONE_ID (optional, read-only token): checks Cloudflare security settings
  STATE_FILE            JSON kept between runs (actions/cache) to spot changed law pages and new advisories
  LIGHTHOUSE_DIR        folder with Lighthouse JSON reports (the workflow runs Lighthouse first)
  AUDIT_DIR             folder with pip-audit / npm-audit output (the workflow runs them first)
"""
import datetime as dt
import difflib
import hashlib
import html
import json
import os
import re
import socket
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

UA = 'LeadGen-Watchdog/1.0 (+site health monitor)'
TIMEOUT = 25

# Pages whose wording changes when the rules change. A change means "read it", not "you broke a law".
LAW_PAGES = {
    'US CAN-SPAM guide (FTC)': 'https://www.ftc.gov/business-guidance/resources/can-spam-act-compliance-guide-business',
    'Gmail sender guidelines': 'https://support.google.com/a/answer/81126?hl=en',
    'Yahoo sender requirements': 'https://senders.yahooinc.com/best-practices/',
    'Outlook.com postmaster (sender rules)': 'https://substrate.office.com/ip-domain-management-snds/postmaster',
    'UK PECR email marketing (ICO)': 'https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/guide-to-pecr/electronic-and-telephone-marketing/electronic-mail-marketing/',
    'EU data protection news (EDPB)': 'https://www.edpb.europa.eu/news/news_en',
    'Australia Spam Act (ACMA)': 'https://www.acma.gov.au/avoid-sending-spam',
}
KEV_URL = 'https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json'
# Exploited-in-the-wild vulnerabilities in anything this app stands on.
STACK_RE = re.compile(r'(django|python|node\.?js|next\.js|react|postgres(ql)?|redis|celery|nginx|caddy|'
                      r'cloudflare|vercel|openssl|npm|pip|gunicorn|docker|firebase)', re.IGNORECASE)
LEAK_PATHS = ('/.env', '/.git/config', '/backend/.env', '/.env.local', '/config.json', '/.DS_Store',
              '/wp-config.php.bak', '/server-status')
SECURITY_HEADERS = {
    'strict-transport-security': 'HSTS (forces HTTPS)',
    'x-content-type-options': 'X-Content-Type-Options: nosniff',
    'referrer-policy': 'Referrer-Policy',
}
LIGHTHOUSE_MIN = 0.9


# --- small helpers -----------------------------------------------------------------------

def env(name, default=''):
    return os.environ.get(name, default).strip()


def urls():
    return [u.strip() for u in env('WATCH_URLS').split(',') if u.strip().startswith('http')]


def fetch(url, method='GET', data=None, headers=None, timeout=TIMEOUT):
    """(status, headers dict, body bytes). Status 0 means the server could not be reached."""
    request = urllib.request.Request(url, data=data, method=method, headers={'User-Agent': UA, **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, {k.lower(): v for k, v in response.headers.items()}, response.read(3_000_000)
    except urllib.error.HTTPError as exc:
        return exc.code, {k.lower(): v for k, v in exc.headers.items()}, exc.read(200_000)
    except (urllib.error.URLError, socket.timeout, ssl.SSLError, ConnectionError, OSError) as exc:
        return 0, {}, str(exc).encode()


def page_text(body):
    text = re.sub(rb'(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>', b' ', body)
    text = re.sub(rb'<[^>]+>', b' ', text).decode('utf-8', 'ignore')
    text = html.unescape(text)
    # Drop things that change on every load (dates, times, counters) so only real edits count.
    text = re.sub(r'\d{1,2}[:/.-]\d{1,2}([:/.-]\d{2,4})?', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def load_state():
    path = Path(env('STATE_FILE', 'watchdog-state.json'))
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def save_state(state):
    Path(env('STATE_FILE', 'watchdog-state.json')).write_text(json.dumps(state, indent=1), encoding='utf-8')


# --- checks ---------------------------------------------------------------------------------

def vercel_challenge(headers):
    return headers.get('x-vercel-mitigated') == 'challenge'


CHALLENGE_NOTE = ('Vercel bot challenge answers automated callers instead of the app. On the backend this BLOCKS '
                  'the GitHub cron, Resend webhooks and Gmail one-click unsubscribe. Vercel -> that project -> '
                  'Firewall: turn Attack Challenge Mode off, or add a bypass rule for /api/outreach/.')


def check_up(url):
    """'' when fine, otherwise what is wrong."""
    started = dt.datetime.now()
    status, headers, body = fetch(url)
    if vercel_challenge(headers):
        return CHALLENGE_NOTE
    seconds = (dt.datetime.now() - started).total_seconds()
    if status == 0:
        return f'unreachable ({body[:120].decode("utf-8", "ignore")})'
    if status >= 500:
        return f'server error {status}'
    if status >= 400 and status not in (401, 403, 405):
        return f'HTTP {status}'
    if seconds > 15:
        return f'very slow ({seconds:.0f}s)'
    return ''


def check_tls(url):
    host = urllib.parse.urlparse(url).hostname
    if not host or not url.startswith('https://'):
        return [f'{url}: not served over HTTPS']
    try:
        context = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=TIMEOUT) as sock:
            with context.wrap_socket(sock, server_hostname=host) as tls:
                cert, version = tls.getpeercert(), tls.version()
    except (OSError, ssl.SSLError) as exc:
        return [f'{host}: TLS handshake failed ({exc})']
    problems = []
    expires = dt.datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
    days = (expires - dt.datetime.utcnow()).days
    if days < 21:
        problems.append(f'{host}: TLS certificate expires in {days} days')
    if version in ('TLSv1', 'TLSv1.1'):
        problems.append(f'{host}: still negotiates old {version}')
    return problems


def check_headers(url):
    status, headers, _ = fetch(url)
    if status == 0 or vercel_challenge(headers):
        return []  # the challenge page is Vercel's, not the app's: its headers say nothing about the app
    host = urllib.parse.urlparse(url).hostname
    problems = [f'{host}: missing {label}' for name, label in SECURITY_HEADERS.items() if name not in headers]
    if 'content-security-policy' not in headers and 'x-frame-options' not in headers:
        problems.append(f'{host}: no clickjacking protection (CSP frame-ancestors or X-Frame-Options)')
    server = headers.get('x-powered-by', '')
    if server:
        problems.append(f'{host}: reveals its software in X-Powered-By: {server}')
    return problems


def check_leaks(url):
    """Secret files that must never be downloadable."""
    base = url.rstrip('/')
    problems = []
    for path in LEAK_PATHS:
        status, headers, body = fetch(base + path)
        if status != 200:
            continue
        sample = body[:2000].decode('utf-8', 'ignore')
        looks_secret = re.search(r'(SECRET|PASSWORD|API_KEY|TOKEN|\[core\]|repositoryformatversion)', sample)
        is_html = 'text/html' in headers.get('content-type', '')
        if looks_secret or not is_html:
            problems.append(f'LEAK: {base + path} is publicly downloadable. Remove it and rotate any keys in it.')
    return problems


def dns_txt(name):
    status, _, body = fetch(f'https://cloudflare-dns.com/dns-query?name={urllib.parse.quote(name)}&type=TXT',
                            headers={'Accept': 'application/dns-json'})
    if status != 200:
        return None
    try:
        answers = json.loads(body).get('Answer') or []
    except ValueError:
        return None
    return [a.get('data', '').replace('" "', '').strip('"') for a in answers]


def check_email_auth(domain):
    if not domain:
        return []
    problems = []
    root = dns_txt(domain)
    if root is not None:
        spf = [r for r in root if r.startswith('v=spf1')]
        if len(spf) != 1:
            problems.append(f'{domain}: needs exactly one SPF record, found {len(spf)}')
    dmarc = dns_txt(f'_dmarc.{domain}')
    if dmarc is not None and not any(r.startswith('v=DMARC1') for r in dmarc):
        problems.append(f'{domain}: no DMARC record (Gmail, Yahoo and Outlook require one)')
    dkim = dns_txt(f'resend._domainkey.{domain}')
    if dkim is not None and not dkim:
        problems.append(f'{domain}: no Resend DKIM key (resend._domainkey). Emails from hello@ will not be signed.')
    send_spf = dns_txt(f'send.{domain}')
    if send_spf is not None and not any(r.startswith('v=spf1') for r in send_spf):
        problems.append(f'send.{domain}: no SPF record for Resend bounces')
    return problems


def check_cloudflare():
    token, zone = env('CLOUDFLARE_API_TOKEN'), env('CLOUDFLARE_ZONE_ID')
    if not (token and zone):
        return [], 'skipped (set CLOUDFLARE_API_TOKEN and CLOUDFLARE_ZONE_ID to enable)'
    status, _, body = fetch(f'https://api.cloudflare.com/client/v4/zones/{zone}/settings',
                            headers={'Authorization': f'Bearer {token}'})
    if status != 200:
        return [f'Cloudflare API refused the token (HTTP {status})'], 'error'
    settings = {s['id']: s.get('value') for s in json.loads(body).get('result', [])}
    wanted = {
        'ssl': (lambda v: v in ('full', 'strict'), 'SSL mode should be Full (strict)'),
        'always_use_https': (lambda v: v == 'on', 'Always Use HTTPS is off'),
        'min_tls_version': (lambda v: v in ('1.2', '1.3'), 'Minimum TLS version should be 1.2 or higher'),
        'browser_check': (lambda v: v == 'on', 'Browser Integrity Check is off'),
        'security_level': (lambda v: v not in ('off', 'essentially_off'), 'Security level is off'),
        'automatic_https_rewrites': (lambda v: v == 'on', 'Automatic HTTPS Rewrites is off'),
    }
    problems = [f'Cloudflare: {msg}' for key, (ok, msg) in wanted.items() if key in settings and not ok(settings[key])]
    return problems, 'checked'


def check_kev(state):
    """New entries in CISA's Known Exploited Vulnerabilities list that touch this app's stack."""
    status, _, body = fetch(KEV_URL, timeout=60)
    if status != 200:
        return [], 'could not download the CISA KEV feed'
    seen = set(state.get('kev_seen', []))
    since = (dt.date.today() - dt.timedelta(days=8)).isoformat()
    found = []
    for item in json.loads(body).get('vulnerabilities', []):
        if item.get('dateAdded', '') < since or item['cveID'] in seen:
            continue
        product = f"{item.get('vendorProject', '')} {item.get('product', '')}".lower()
        if STACK_RE.search(product):
            found.append(f"{item['cveID']} ({item.get('vendorProject')} {item.get('product')}): "
                         f"{item.get('shortDescription', '')[:220]} Fix: {item.get('requiredAction', '')[:120]}")
            seen.add(item['cveID'])
    state['kev_seen'] = sorted(seen)[-500:]
    return found, 'checked'


def check_law_pages(state):
    """Compare each page's words with last week's. Small noise (menus, dates) is ignored; real edits are not."""
    texts = state.setdefault('law_text', {})
    state.pop('law_pages', None)
    changed, errors = [], []
    for name, url in LAW_PAGES.items():
        status, _, body = fetch(url)
        if status != 200:
            errors.append(f'{name}: could not fetch (HTTP {status})')
            continue
        words = page_text(body)[:60000].split()
        before = texts.get(name)
        if before:
            ratio = difflib.SequenceMatcher(None, before, words, autojunk=False).ratio()
            if ratio < 0.97:
                changed.append(f'{name} changed ({round((1 - ratio) * 100)}% of the text): {url}')
        texts[name] = words
    return changed, errors


def lighthouse_scores():
    folder = Path(env('LIGHTHOUSE_DIR', 'lighthouse'))
    results = []
    for report in sorted(folder.glob('*.json')) if folder.is_dir() else []:
        try:
            data = json.loads(report.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        cats = data.get('categories') or {}
        scores = {k: cats[k]['score'] for k in ('performance', 'accessibility', 'best-practices', 'seo')
                  if k in cats and cats[k].get('score') is not None}
        if scores:
            results.append((data.get('finalDisplayedUrl') or data.get('finalUrl') or report.stem, scores))
    return results


def dependency_audits():
    folder = Path(env('AUDIT_DIR', 'audit'))
    problems = []
    pip_file, npm_file = folder / 'pip-audit.json', folder / 'npm-audit.json'
    try:
        pip_data = json.loads(pip_file.read_text(encoding='utf-8'))
        for dep in pip_data.get('dependencies', []):
            for vuln in dep.get('vulns', []):
                fix = ', '.join(vuln.get('fix_versions', [])) or 'no fix yet'
                problems.append(f"Python {dep['name']} {dep.get('version')}: {vuln['id']} (upgrade to {fix})")
    except (OSError, ValueError):
        pass
    try:
        npm_data = json.loads(npm_file.read_text(encoding='utf-8'))
        for name, vuln in (npm_data.get('vulnerabilities') or {}).items():
            if vuln.get('severity') in ('high', 'critical'):
                problems.append(f"npm {name}: {vuln['severity']} vulnerability (run npm audit fix)")
    except (OSError, ValueError):
        pass
    return problems


# --- alerts ---------------------------------------------------------------------------------

def send_email(subject, text):
    key, to = env('RESEND_API_KEY'), env('ALERT_EMAIL')
    if not (key and to):
        return False
    payload = json.dumps({'from': env('ALERT_FROM') or 'LeadGen Watchdog <hello@zubairhussain.xyz>',
                          'to': [to], 'subject': subject[:200], 'text': text}).encode()
    status, _, body = fetch('https://api.resend.com/emails', method='POST', data=payload,
                            headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'})
    if status >= 300 or status == 0:
        print(f'Email failed ({status}): {body[:300]!r}')
        return False
    return True


def github_issue(title, text, close=False):
    """Fallback alert: open (or comment on / close) an issue. GitHub emails the repo owner."""
    token, repo = env('GITHUB_TOKEN'), env('GITHUB_REPOSITORY')
    if not (token and repo):
        return False
    api = f'https://api.github.com/repos/{repo}/issues'
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json',
               'Content-Type': 'application/json'}
    status, _, body = fetch(f'{api}?state=open&labels=watchdog&per_page=50', headers=headers)
    existing = next((i for i in (json.loads(body) if status == 200 else []) if i['title'] == title), None)
    if close:
        if existing:
            fetch(f"{api}/{existing['number']}/comments", 'POST', json.dumps({'body': text}).encode(), headers)
            fetch(f"{api}/{existing['number']}", 'PATCH', json.dumps({'state': 'closed'}).encode(), headers)
        return True
    if existing:
        fetch(f"{api}/{existing['number']}/comments", 'POST', json.dumps({'body': text}).encode(), headers)
    else:
        fetch(api, 'POST', json.dumps({'title': title, 'body': text, 'labels': ['watchdog']}).encode(), headers)
    return True


def open_issue_exists(title):
    token, repo = env('GITHUB_TOKEN'), env('GITHUB_REPOSITORY')
    if not (token and repo):
        return False
    status, _, body = fetch(f'https://api.github.com/repos/{repo}/issues?state=open&labels=watchdog&per_page=50',
                            headers={'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json'})
    return status == 200 and any(i['title'] == title for i in json.loads(body))


def alert(subject, text):
    emailed = send_email(subject, text)
    github_issue(subject if not subject.startswith('[DOWN]') else 'Site down', text)
    print(('Emailed: ' if emailed else 'Issue only: ') + subject)


# --- modes ----------------------------------------------------------------------------------

def run_uptime():
    down = {u: why for u in urls() if (why := check_up(u))}
    if down:
        # Retry once: one blip is not an outage.
        down = {u: why for u in down if (why := check_up(u))}
    title = 'Site down'
    already = open_issue_exists(title)
    if down and not already:
        lines = [f'- {u}: {why}' for u, why in down.items()]
        alert('[DOWN] ' + ', '.join(urllib.parse.urlparse(u).hostname for u in down),
              'These addresses are not answering properly:\n' + '\n'.join(lines)
              + '\n\nCheck Vercel / Cloudflare status and your latest deploy. You get one email per outage.')
    elif not down and already:
        send_email('[RECOVERED] All sites are back up', 'Every watched address answers normally again.')
        github_issue(title, 'Recovered: every watched address answers normally.', close=True)
    print('down: ' + (', '.join(down) or 'none'))
    return 0  # never fail the job: a red run would make GitHub email you every 15 minutes


def run_weekly():
    state = load_state()
    sections = []

    def add(title, items, note=''):
        if items:
            sections.append(f'## {title}\n' + '\n'.join(f'- {i}' for i in items) + (f'\n{note}' if note else ''))

    watched = urls()
    add('Down or failing', [f'{u}: {w}' for u in watched if (w := check_up(u))])
    add('Leaked files (urgent)', [p for u in watched for p in check_leaks(u)])
    add('HTTPS / TLS', [p for u in watched for p in check_tls(u)])
    add('Security headers', [p for u in watched for p in check_headers(u)],
        'Add them in Cloudflare (Rules -> Transform Rules -> Response headers) or in the app.')
    add('Email authentication (spam folder risk)', check_email_auth(env('EMAIL_DOMAIN')))
    cloudflare, cf_status = check_cloudflare()
    add('Cloudflare security settings', cloudflare)
    add('Vulnerable dependencies', dependency_audits(), 'Upgrade these packages and redeploy.')
    if env('GITLEAKS_OUTCOME') == 'failure':
        add('Secrets committed to git (urgent)', ['gitleaks found a key or password in the repository history.'],
            'Rotate that key now (it is public if the repo is public), then remove it from the code.')
    kev, kev_status = check_kev(state)
    add('New actively exploited vulnerabilities in your stack (CISA KEV)', kev,
        'These are being used in real attacks right now. Update the affected software.')
    changed, law_errors = check_law_pages(state)
    add('Email law / sender rule pages changed (review and tell Claude what changed)', changed,
        'A change can be small wording. Open the page; if a rule changed, update outreach/compliance.py.')
    low = []
    for url, scores in lighthouse_scores():
        weak = {k: round(v * 100) for k, v in scores.items() if v < LIGHTHOUSE_MIN}
        if weak:
            low.append(f'{url}: ' + ', '.join(f'{k} {v}' for k, v in weak.items()))
    add('Lighthouse below 90 (speed / SEO / accessibility)', low)
    save_state(state)

    status_lines = [f'Cloudflare: {cf_status}', f'CISA KEV: {kev_status}',
                    f'Lighthouse reports: {len(lighthouse_scores())}', f'Watched URLs: {len(watched)}']
    status_lines += law_errors
    if not sections:
        print('All checks passed.\n' + '\n'.join(status_lines))
        return 0
    body = ('Your weekly LeadGen security & compliance watch found things that need you.\n\n'
            + '\n\n'.join(sections) + '\n\n---\n' + '\n'.join(status_lines))
    urgent = any(s.startswith(('## Leaked', '## Down', '## New actively', '## Secrets')) for s in sections)
    alert(f"{'[URGENT] ' if urgent else ''}Weekly security & compliance watch: {len(sections)} area(s) need attention",
          body)
    print(body)
    return 0


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'weekly'
    sys.exit(run_uptime() if mode == 'uptime' else run_weekly())
