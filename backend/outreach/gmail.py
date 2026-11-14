"""Minimal Gmail API client (OAuth refresh token + messages.send).

Uses plain `requests` so there is no extra Google SDK dependency, and so the
whole thing is easy to mock in tests.
"""
import base64
import logging

import requests
from django.conf import settings

from .mime import build_mime  # noqa: F401  (also used by tests as gmail.build_mime)

logger = logging.getLogger(__name__)

TOKEN_URL = 'https://oauth2.googleapis.com/token'
AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
SEND_URL = 'https://gmail.googleapis.com/gmail/v1/users/me/messages/send'

# gmail.send to send; gmail.readonly so the reply/bounce detector (next step)
# can read threads without asking you to re-authorise.
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
]


class GmailError(Exception):
    """Raised when Gmail rejects a request."""


def is_configured():
    return all([
        settings.GOOGLE_CLIENT_ID,
        settings.GOOGLE_CLIENT_SECRET,
        settings.GOOGLE_REFRESH_TOKEN,
        settings.OUTREACH_FROM_EMAIL,
    ])


def get_access_token():
    response = requests.post(TOKEN_URL, data={
        'client_id': settings.GOOGLE_CLIENT_ID,
        'client_secret': settings.GOOGLE_CLIENT_SECRET,
        'refresh_token': settings.GOOGLE_REFRESH_TOKEN,
        'grant_type': 'refresh_token',
    }, timeout=15)
    if response.status_code != 200:
        # invalid_grant here usually means the refresh token expired
        # (7-day limit for "External" apps left in Testing mode) or was revoked.
        raise GmailError(f"Token refresh failed ({response.status_code}): {response.text[:300]}")
    return response.json()['access_token']


def send_message(to_email, subject, body, list_unsubscribe=True, html=None, message_id=None,
                 in_reply_to='', references='', thread_id='', unsubscribe_url=''):
    """Send an email (plain text, plus HTML when given). Returns (gmail_message_id, gmail_thread_id)."""
    mime = build_mime(to_email, subject, body, list_unsubscribe=list_unsubscribe, html=html,
                      message_id=message_id, in_reply_to=in_reply_to, references=references,
                      unsubscribe_url=unsubscribe_url)
    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode('ascii')
    payload = {'raw': raw}
    if thread_id:
        payload['threadId'] = thread_id
    response = requests.post(
        SEND_URL,
        headers={'Authorization': f'Bearer {get_access_token()}'},
        json=payload,
        timeout=30,
    )
    if response.status_code not in (200, 201):
        raise GmailError(f"Gmail send failed ({response.status_code}): {response.text[:300]}")
    data = response.json()
    logger.info("Gmail sent message %s to %s", data.get('id'), to_email)
    return data.get('id', ''), data.get('threadId', '')
