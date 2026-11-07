"""Find local businesses listed on Yelp, Nextdoor and True Local (Australia), then find their own email.

How, and why not "scrape the sites directly":
- Yelp: the official Yelp Fusion API (YELP_API_KEY). Allowed use; it never returns emails.
- Nextdoor and True Local: found through Google search results via SerpAPI (site: queries). Both sites
  block bots (True Local answers scripts with a Cloudflare challenge; Nextdoor is login-walled), and this
  code does not try to get around that. Their pages are never fetched.
- For each business name, SerpAPI Google Maps gives the business's OWN website and phone, and the email
  is read from that website's public contact pages (LeadGenerator._extract_active_email_from_website).

Emails only come from the business's own published website, which is also what regional email law
(inferred consent / legitimate interest for published business addresses) relies on.
"""
import logging
import re

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

YELP_URL = 'https://api.yelp.com/v3/businesses/search'
TITLE_SPLIT_RE = re.compile(r'\s+[-|–—]\s+')
SITE_QUERIES = {
    'nextdoor': 'site:nextdoor.com/pages',
    'truelocal': 'site:truelocal.com.au',
    'yelp': 'site:yelp.com/biz',
}
DIRECTORY_SOURCES = ('yelp', 'nextdoor', 'truelocal')


def clean_name(title):
    """'Joe's Plumbing - Austin, TX | Nextdoor' -> "Joe's Plumbing"."""
    name = TITLE_SPLIT_RE.split((title or '').strip())[0].strip()
    return re.sub(r'^\d+\.\s*', '', name)[:120]


def _norm(text):
    return re.sub(r'[^a-z0-9]+', ' ', (text or '').lower()).strip()


def _names_match(wanted, found):
    a, b = _norm(wanted), _norm(found)
    return bool(a and b) and (a == b or a in b or b in a)


def yelp_businesses(category, location, limit):
    if not settings.YELP_API_KEY:
        return None  # not configured; caller falls back to search results
    try:
        response = requests.get(
            YELP_URL, timeout=20, headers={'Authorization': f'Bearer {settings.YELP_API_KEY}'},
            params={'term': category, 'location': location, 'limit': min(limit, 50)},
        )
        response.raise_for_status()
        items = response.json().get('businesses', [])
    except (requests.RequestException, ValueError) as exc:
        logger.warning('Yelp API failed: %s', exc)
        return []
    return [{
        'name': item.get('name', ''), 'phone': item.get('phone', ''),
        'address': ', '.join((item.get('location') or {}).get('display_address', [])),
        'directory_url': item.get('url', ''),
    } for item in items if item.get('name')]


def search_result_businesses(source, category, location, limit, client):
    query = f'{SITE_QUERIES[source]} {category} {location}'
    try:
        results = client.search({'q': query, 'num': min(limit * 2, 40)})
    except Exception as exc:  # serpapi raises its own error types
        logger.warning('%s search failed: %s', source, exc)
        return []
    found, seen = [], set()
    for res in results.get('organic_results', []):
        name = clean_name(res.get('title'))
        key = _norm(name)
        if not name or key in seen or key in ('nextdoor', 'yelp', 'true local', 'truelocal'):
            continue
        seen.add(key)
        found.append({'name': name, 'phone': '', 'address': '', 'directory_url': res.get('link', '')})
        if len(found) >= limit:
            break
    return found


def resolve_place(client, name, location):
    """Look the business up on Google Maps; return its own website/phone/address or None."""
    try:
        results = client.search({'engine': 'google_maps', 'type': 'search', 'q': f'{name}, {location}'})
    except Exception as exc:
        logger.warning('Maps lookup failed for %s: %s', name, exc)
        return None
    candidates = [results['place_results']] if results.get('place_results') else results.get('local_results', [])
    for item in candidates:
        if _names_match(name, item.get('title')) and item.get('website'):
            return item
    return None


def discover(generator, source, category, location):
    """Return lead dicts (email, phone, source, ...) for one directory. Never raises."""
    if source not in DIRECTORY_SOURCES or not location:
        return []
    limit = settings.DIRECTORY_MAX_PER_RUN
    client = None
    if generator.serpapi_key:
        import serpapi
        client = serpapi.Client(api_key=generator.serpapi_key)

    businesses = yelp_businesses(category, location, limit) if source == 'yelp' else None
    if businesses is None:
        if client is None:
            logger.warning('%s discovery needs SERPAPI_KEY (or YELP_API_KEY for Yelp)', source)
            return []
        businesses = search_result_businesses(source, category, location, limit, client)
    if client is None:
        logger.warning('Finding business websites needs SERPAPI_KEY')
        return []

    leads = []
    for business in businesses[:limit]:
        place = resolve_place(client, business['name'], location)
        if place is None:
            continue
        email = generator._extract_active_email_from_website(place['website'])
        if not email:
            continue
        leads.append({
            'email': email,
            'phone': place.get('phone') or business['phone'],
            'source': source,
            'category': category,
            'location': place.get('address') or business['address'] or location,
            'link': place['website'],
            'problem_statement': f"Local business: {place.get('title') or business['name']}. Listed on {source}.",
        })
    logger.info('%s discovery: %d businesses -> %d leads', source, len(businesses), len(leads))
    return leads
