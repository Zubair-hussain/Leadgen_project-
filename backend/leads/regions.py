"""Work out which country (and legal region) a lead is in. No imports from other apps."""
import re

import phonenumbers

EU_COUNTRIES = {
    'AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'GR', 'HU', 'IE', 'IT', 'LV', 'LT',
    'LU', 'MT', 'NL', 'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE', 'IS', 'LI', 'NO', 'CH',
}

# Region -> time zone used for the 9-17 business-hours send window.
REGION_TZ = {'US': 'America/Chicago', 'UK': 'Europe/London', 'EU': 'Europe/Paris', 'AU': 'Australia/Sydney'}

COUNTRY_WORDS = {
    'US': ('united states', 'usa', 'u.s.a', 'u.s.', ', us'),
    'GB': ('united kingdom', 'england', 'scotland', 'wales', 'northern ireland', ', uk', 'great britain'),
    'AU': ('australia',),
    'DE': ('germany', 'deutschland'), 'AT': ('austria',), 'FR': ('france',), 'ES': ('spain',),
    'IT': ('italy',), 'NL': ('netherlands', 'holland'), 'IE': ('ireland',), 'PT': ('portugal',),
    'BE': ('belgium',), 'SE': ('sweden',), 'DK': ('denmark',), 'FI': ('finland',), 'PL': ('poland',),
}
AU_STATES = r'\b(NSW|VIC|QLD|WA|SA|TAS|ACT|NT)\b'
US_STATES = (
    'AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND '
    'OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC'
).split()
US_STATE_RE = re.compile(r',\s*(' + '|'.join(US_STATES) + r')\b(?:\s+\d{5})?\s*(?:,|$|\s)')
AU_POSTCODE_RE = re.compile(r'\b(NSW|VIC|QLD|WA|SA|TAS|ACT|NT)\s+\d{4}\b')
TLD_COUNTRY = {
    'au': 'AU', 'uk': 'GB', 'us': 'US', 'de': 'DE', 'at': 'AT', 'fr': 'FR', 'es': 'ES', 'it': 'IT',
    'nl': 'NL', 'ie': 'IE', 'pt': 'PT', 'be': 'BE', 'se': 'SE', 'dk': 'DK', 'fi': 'FI', 'pl': 'PL',
}


def region_of(country):
    country = (country or '').upper()
    if country == 'US':
        return 'US'
    if country in ('GB', 'UK'):
        return 'UK'
    if country == 'AU':
        return 'AU'
    if country in EU_COUNTRIES:
        return 'EU'
    return ''


def _from_phone(phone):
    if not phone or not str(phone).strip().startswith('+'):
        return ''
    try:
        return phonenumbers.region_code_for_number(phonenumbers.parse(str(phone), None)) or ''
    except phonenumbers.NumberParseException:
        return ''


def _from_text(text):
    low = f" {(text or '').lower()} "
    for code, words in COUNTRY_WORDS.items():
        if any(w in low for w in words):
            return code
    if AU_POSTCODE_RE.search(text or ''):
        return 'AU'
    if US_STATE_RE.search(text or ''):
        return 'US'
    return ''


def _from_domain(value):
    host = (value or '').lower().split('@')[-1].split('//')[-1].split('/')[0]
    tld = host.rsplit('.', 1)[-1] if '.' in host else ''
    return TLD_COUNTRY.get(tld, '')


def detect_country(country='', location='', phone='', email='', link=''):
    """Best guess at an ISO-2 country code, or '' when nothing is certain."""
    country = (country or '').strip().upper()
    if len(country) == 2:
        return 'GB' if country == 'UK' else country
    return (_from_text(location) or _from_phone(phone) or _from_domain(link) or _from_domain(email))
