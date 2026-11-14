"""Turn a plain-text outreach email into what the recipient receives: text + branded HTML.

The body stays a personal letter (no banners, images or tracking pixels, which spam
filters and busy people both distrust). The brand lives in the signature: the ZH. mark
from zubairhussain.xyz in Instrument Serif with the red full stop, on the same ink card.
"""
import re

from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import escape
from django.utils.safestring import mark_safe

from . import compliance

BRAND = {'ink': '#0a0a0a', 'paper': '#F5F4F0', 'red': '#C8141E', 'glow': 'rgba(200,20,30,0.55)', 'edge': '#2a1214'}
URL_RE = re.compile(r'(https?://[^\s<]+[^\s<.,;:!?)])')


def portfolio_label():
    url = settings.OUTREACH_PORTFOLIO_URL or ''
    return re.sub(r'^https?://(www\.)?', '', url).rstrip('/')


def signature_text():
    if not settings.OUTREACH_SIGNATURE:
        return ''
    lines = ['--', settings.OUTREACH_FROM_NAME or 'Zubair Hussain']
    second = ' | '.join(part for part in (settings.OUTREACH_SENDER_TITLE, portfolio_label()) if part)
    if second:
        lines.append(second)
    if settings.OUTREACH_SERVICES:
        lines.append(' · '.join(settings.OUTREACH_SERVICES))
    if settings.OUTREACH_BOOKING_URL:
        lines.append(f'Book a 15-min call: {settings.OUTREACH_BOOKING_URL}')
    return '\n'.join(lines)


def text_version(body, region='', source='', unsubscribe_url=''):
    """Plain-text part: body, signature, then the opt-out line and the legal footer."""
    parts = [body.rstrip()]
    signature = signature_text()
    if signature:
        parts.append(signature)
    opt_out = settings.OUTREACH_OPT_OUT_LINE.strip()
    if opt_out:
        parts.append(opt_out)
    footer = compliance.footer_lines(region, source)
    if unsubscribe_url:
        footer = footer + [f'Unsubscribe with one click: {unsubscribe_url}']
    if footer:
        parts.append('\n'.join(footer))
    return '\n\n'.join(parts)


def _paragraph_html(paragraph):
    html = escape(paragraph)
    html = URL_RE.sub(
        lambda m: f'<a href="{m.group(1)}" style="color:{BRAND["red"]};text-decoration:underline;">{m.group(1)}</a>',
        html,
    )
    return mark_safe(html.replace('\n', '<br>'))


def _signature_context():
    return {
        'name': settings.OUTREACH_FROM_NAME or 'Zubair Hussain',
        'title': settings.OUTREACH_SENDER_TITLE,
        'portfolio_url': settings.OUTREACH_PORTFOLIO_URL,
        'portfolio_label': portfolio_label(),
        'services': settings.OUTREACH_SERVICES,
        'booking_url': settings.OUTREACH_BOOKING_URL,
        'brand': BRAND,
    }


def html_version(subject, body, region='', source='', unsubscribe_url=''):
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', body.strip()) if p.strip()]
    return render_to_string('outreach/email/cold.html', {
        'subject': subject,
        'paragraphs': [_paragraph_html(p) for p in paragraphs],
        'signature': settings.OUTREACH_SIGNATURE,
        'opt_out': settings.OUTREACH_OPT_OUT_LINE.strip(),
        'footer_lines': compliance.footer_lines(region, source),
        'unsubscribe_url': unsubscribe_url,
        **_signature_context(),
    })


def signature_html():
    """Just the ZH. card, to paste into Hostinger webmail as your signature."""
    return render_to_string('outreach/email/_signature.html', _signature_context())


def compose(subject, body, region='', source='', unsubscribe_url=''):
    """Return (text, html). html is None when OUTREACH_HTML_EMAIL is off."""
    return (text_version(body, region, source, unsubscribe_url),
            html_version(subject, body, region, source, unsubscribe_url) if settings.OUTREACH_HTML_EMAIL else None)
