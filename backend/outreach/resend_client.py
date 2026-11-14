"""Send through Resend's HTTP API (hello@zubairhussain.xyz). Works on Vercel, where SMTP ports can be slow.

Resend signs every message with DKIM for your domain and uses send.<your domain> as the bounce
(Return-Path) domain, so SPF and DKIM both align with DMARC once the DNS records Resend shows
you are added. Replies go to OUTREACH_REPLY_TO (a mailbox you actually read), because Resend
only sends. Bounces and spam complaints come back through the webhook in outreach/webhooks.py.
"""
import logging

import requests
from django.conf import settings

from .mime import list_unsubscribe_header, new_message_id

logger = logging.getLogger(__name__)

API_URL = 'https://api.resend.com/emails'


class ResendError(Exception):
    """Raised when Resend refuses the API key or the message."""


def is_configured():
    return bool(settings.RESEND_API_KEY and settings.OUTREACH_FROM_EMAIL)


def _from_header():
    name, email = settings.OUTREACH_FROM_NAME, settings.OUTREACH_FROM_EMAIL
    return f'{name} <{email}>' if name else email


def build_payload(to_email, subject, body, list_unsubscribe=True, html=None, message_id=None,
                  in_reply_to='', references='', unsubscribe_url=''):
    headers = {'Message-ID': message_id or new_message_id()}
    if in_reply_to:
        headers['In-Reply-To'] = in_reply_to
        headers['References'] = references or in_reply_to
    if list_unsubscribe:
        headers['List-Unsubscribe'] = list_unsubscribe_header(unsubscribe_url)
        if unsubscribe_url:
            headers['List-Unsubscribe-Post'] = 'List-Unsubscribe=One-Click'
    payload = {
        'from': _from_header(),
        'to': [to_email],
        'subject': subject,
        'text': body,
        'headers': headers,
    }
    if html:
        payload['html'] = html
    reply_to = settings.OUTREACH_REPLY_TO.strip()
    if reply_to and reply_to.lower() != settings.OUTREACH_FROM_EMAIL.lower():
        payload['reply_to'] = [reply_to]
    return payload


def send_message(to_email, subject, body, list_unsubscribe=True, html=None, message_id=None,
                 in_reply_to='', references='', thread_id='', unsubscribe_url=''):  # pylint: disable=unused-argument
    """Send one email. Returns (resend_email_id, '') to match the other transports' (id, thread) shape.

    The Resend id is what bounce/complaint webhooks quote, so it is stored as the provider id.
    """
    if not is_configured():
        raise ResendError('RESEND_API_KEY is not set.')
    payload = build_payload(to_email, subject, body, list_unsubscribe=list_unsubscribe, html=html,
                            message_id=message_id, in_reply_to=in_reply_to, references=references,
                            unsubscribe_url=unsubscribe_url)
    try:
        response = requests.post(
            API_URL,
            json=payload,
            headers={
                'Authorization': f'Bearer {settings.RESEND_API_KEY}',
                # Same message retried after a timeout is delivered once, not twice.
                'Idempotency-Key': payload['headers']['Message-ID'][:256],
            },
            timeout=30,
        )
    except requests.RequestException as exc:
        raise ResendError(f'Could not reach Resend: {exc}') from exc
    if response.status_code >= 400:
        try:
            detail = response.json().get('message', response.text)
        except ValueError:
            detail = response.text
        raise ResendError(f'Resend refused the email ({response.status_code}): {str(detail)[:300]}')
    email_id = (response.json() or {}).get('id', '')
    logger.info('Resend sent %s to %s', email_id, to_email)
    return email_id, ''
