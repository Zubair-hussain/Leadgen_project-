"""Fresh business facts from SerpAPI (Google Maps), used three ways:

1. the Gemini writer gets real, current facts to personalise a draft;
2. just before sending, a business that now shows as closed is skipped;
3. an email sent WITHOUT a person approving it needs a confirmed match, or it is held.
"""
import logging
import re
from datetime import timedelta
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.utils import timezone

from .models import LeadResearch

logger = logging.getLogger(__name__)

SEARCH_URL = 'https://serpapi.com/search.json'
NAME_RE = re.compile(r'Local business:\s*(.+?)\.\s', re.IGNORECASE)
Status = LeadResearch.Status


def _domain(value):
    value = (value or '').strip().lower()
    if '@' in value and '//' not in value:
        value = value.rsplit('@', 1)[-1]
    host = urlparse(value if '//' in value else f'//{value}').netloc or value
    return host.removeprefix('www.')


def business_name(lead):
    match = NAME_RE.search((lead.problem_statement or '') + ' ')
    return match.group(1).strip() if match else ''


def _is_match(item, lead, name):
    wanted = {_domain(lead.link), _domain(lead.email)} - {''}
    site = _domain(item.get('website'))
    if site and any(site == w or site.endswith('.' + w) or w.endswith('.' + site) for w in wanted):
        return True
    return bool(name) and (item.get('title') or '').strip().casefold() == name.casefold()


def _closed_state(item):
    text = ' '.join(str(item.get(key) or '') for key in ('open_state', 'extensions', 'title')).lower()
    if item.get('permanently_closed') or 'permanently closed' in text:
        return 'permanently closed'
    if item.get('temporarily_closed') or 'temporarily closed' in text:
        return 'temporarily closed'
    return ''


def _facts(item, lead):
    site = item.get('website') or ''
    return {
        'name': item.get('title') or '',
        'rating': item.get('rating'),
        'reviews': item.get('reviews'),
        'address': item.get('address') or '',
        'website': site,
        'has_website': bool(site),
        'types': (item.get('type') or [])[:3] if isinstance(item.get('type'), list) else [],
        'website_changed': bool(site and lead.link and _domain(site) != _domain(lead.link)),
    }


def lookup(lead):
    """Query SerpAPI and return (status, data, note). Never raises."""
    if not settings.SERPAPI_KEY:
        return Status.ERROR, {}, 'SERPAPI_KEY is not set.'
    name = business_name(lead)
    query = ', '.join(part for part in (name or _domain(lead.email), lead.location) if part)
    try:
        response = requests.get(SEARCH_URL, params={
            'engine': 'google_maps', 'type': 'search', 'q': query, 'api_key': settings.SERPAPI_KEY,
        }, timeout=30)
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        return Status.ERROR, {}, f'SerpAPI request failed: {exc}'[:300]
    if response.status_code != 200 or payload.get('error'):
        return Status.ERROR, {}, f"SerpAPI error: {payload.get('error') or response.status_code}"[:300]

    candidates = [payload['place_results']] if payload.get('place_results') else payload.get('local_results') or []
    item = next((c for c in candidates if _is_match(c, lead, name)), None)
    if item is None:
        return Status.NO_MATCH, {}, 'No result matched this business name or website.'
    data = _facts(item, lead)
    closed = _closed_state(item)
    if closed:
        data['closed'] = closed
        return Status.CLOSED, data, f'Google Maps says this business is {closed}.'
    return Status.OK, data, ''


def _lookups_today():
    start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    return LeadResearch.objects.filter(checked_at__gte=start).count()


def get_research(lead, force=False):
    """Return the lead's research, refreshing it when it is older than the freshness limit."""
    existing = LeadResearch.objects.filter(lead=lead).first()
    if not settings.OUTREACH_RESEARCH_ENABLED:
        return existing
    max_age = timedelta(days=settings.OUTREACH_RESEARCH_MAX_AGE_DAYS)
    if existing and not force and timezone.now() - existing.checked_at < max_age and existing.status != Status.ERROR:
        return existing
    if _lookups_today() >= settings.OUTREACH_RESEARCH_DAILY_MAX and existing:
        return existing  # protect SerpAPI credits; keep the older facts
    status, data, note = lookup(lead)
    if status == Status.ERROR and existing:
        existing.note = note
        existing.save(update_fields=['note'])
        return existing  # a hiccup must not erase good facts
    research, _ = LeadResearch.objects.update_or_create(
        lead=lead, defaults={'status': status, 'data': data, 'note': note, 'checked_at': timezone.now()})
    return research


def send_blocker(message):
    """Return a reason this message must not go out now, or ''. Run right before sending."""
    if not message.lead_id or not settings.OUTREACH_RESEARCH_ENABLED:
        return ''
    research = get_research(message.lead)
    if research is None:
        return 'Business could not be checked, so it was not auto-sent.' if message.auto_approved else ''
    if research.status == Status.CLOSED:
        return f'{research.note} Not sent.'
    if message.auto_approved and research.status != Status.OK:
        return f'Not auto-sent: business could not be confirmed ({research.note or research.status}).'
    return ''


def summary_line(research):
    """One human line for review emails and pages."""
    if research is None:
        return 'No SerpAPI details yet.'
    if research.status != Status.OK:
        return f'SerpAPI: {research.get_status_display()}. {research.note}'.strip()
    data = research.data
    bits = [data.get('name')]
    if data.get('rating'):
        bits.append(f"{data['rating']} stars ({data.get('reviews') or 0} reviews)")
    bits.append('has a website' if data.get('has_website') else 'no website listed')
    if data.get('website_changed'):
        bits.append('website differs from the one we stored')
    return 'SerpAPI: ' + ', '.join(str(b) for b in bits if b)
