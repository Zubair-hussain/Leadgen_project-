"""One door for every outgoing email, whichever transport is configured.

OUTREACH_TRANSPORT=smtp   your own mailbox (Hostinger: zubair@zubairhussain.xyz). The default.
OUTREACH_TRANSPORT=gmail  the Gmail API with an OAuth refresh token (see docs/outreach.md).
"""
import smtplib

from django.conf import settings

from . import gmail, smtp_client
from .mime import new_message_id  # noqa: F401  (re-exported for callers)

ERRORS = (gmail.GmailError, smtp_client.SmtpError, smtplib.SMTPException, OSError)


def transport():
    return 'gmail' if settings.OUTREACH_TRANSPORT == 'gmail' else 'smtp'


def client():
    return gmail if transport() == 'gmail' else smtp_client


def is_configured():
    return client().is_configured()


def send_message(to_email, subject, body, list_unsubscribe=True, **extra):
    """Returns (provider_message_id, provider_thread_id). Raises one of ERRORS."""
    return client().send_message(to_email, subject, body, list_unsubscribe=list_unsubscribe, **extra)
