"""Cold-email rules per region (US CAN-SPAM, UK/EU GDPR + PECR/ePrivacy, Australia Spam Act 2003).

This enforces the practical requirements in code. It is not legal advice: have a lawyer confirm
the rules for the countries you actually target.

What is enforced before every send:
- the recipient's country is known and not on OUTREACH_BLOCKED_COUNTRIES (default DE, AT, where
  B2B cold email needs prior consent);
- UK/EU/AU: business mailboxes only (personal mailboxes such as gmail.com need consent);
- a real sender identity and postal address are configured (required by all three regimes);
- every email carries a working opt-out, the sender's identity and address, and for UK/EU/AU
  a line saying where the address came from. Opt-outs are suppressed at once (inbox watch).
"""
from django.conf import settings

from leads.regions import REGION_TZ, detect_country, region_of

SOURCE_NAMES = {
    'yelp': 'Yelp', 'nextdoor': 'Nextdoor', 'truelocal': 'True Local',
    'google-maps': 'Google Maps', 'apify-maps': 'Google Maps',
}
REGIONS = ('US', 'UK', 'EU', 'AU')


def blocked_countries():
    return {c.strip().upper() for c in str(settings.OUTREACH_BLOCKED_COUNTRIES).split(',') if c.strip()}


def lead_country(lead):
    if lead is None:
        return ''
    return detect_country(getattr(lead, 'country', ''), lead.location, lead.phone, lead.email, lead.link)


def message_country(message):
    return lead_country(message.lead) if message.lead_id else detect_country(email=message.to_email)


def message_region(message):
    return region_of(message_country(message))


def timezone_name(region):
    return REGION_TZ.get(region) or settings.TIME_ZONE


def is_freemail(email):
    domain = (email or '').rsplit('@', 1)[-1].lower()
    return domain in {d.lower() for d in settings.OUTREACH_FREEMAIL_DOMAINS}


def problems(message):
    """First reason this email breaks a regional rule, or ''."""
    if not settings.OUTREACH_COMPLIANCE_ENABLED:
        return ''
    country = message_country(message)
    region = region_of(country)
    if not region:
        if settings.OUTREACH_REQUIRE_REGION:
            return 'Recipient country is unknown, so the legal rules cannot be applied.'
    elif country in blocked_countries():
        return f'Cold email to {country} needs prior consent, so it is blocked.'
    elif region in ('UK', 'EU', 'AU') and is_freemail(message.to_email):
        return f'Personal mailboxes need consent in the {region}; business addresses only.'
    if not settings.OUTREACH_DRY_RUN and not settings.OUTREACH_SENDER_ADDRESS.strip():
        return 'Set OUTREACH_SENDER_ADDRESS (a postal address is required in every email).'
    return ''


def footer_lines(region, source=''):
    """Legal footer lines, appended under the opt-out line."""
    name = settings.OUTREACH_FROM_NAME or 'Zubair Hussain'
    address = settings.OUTREACH_SENDER_ADDRESS.strip()
    sender = ', '.join(p for p in (name, settings.OUTREACH_SENDER_TITLE, address) if p)
    lines = [f'Sent by {sender}.']
    where = SOURCE_NAMES.get(source, '')
    origin = f'your public listing on {where}' if where else 'publicly listed business details'
    if region in ('UK', 'EU'):
        lines.append(f'I wrote to this business address because it appears in {origin}, '
                     'and I think my work could be relevant to you (legitimate interest). '
                     'You can object at any time by replying "unsubscribe" and I will stop and erase your details.')
    elif region == 'AU':
        lines.append(f'I wrote to this business address because it is published in {origin}. '
                     'Reply "unsubscribe" at any time and I will stop contacting you.')
    if settings.OUTREACH_PRIVACY_URL and region in ('UK', 'EU', 'AU'):
        lines.append(f'Privacy notice: {settings.OUTREACH_PRIVACY_URL}')
    return lines
