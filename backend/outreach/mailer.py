"""One door for every outgoing email, whichever transport is configured.

OUTREACH_TRANSPORT=smtp   your own mailbox (Hostinger: zubair@zubairhussain.xyz). The default.
OUTREACH_TRANSPORT=resend Resend's HTTP API (hello@zubairhussain.xyz). Best deliverability on Vercel.
OUTREACH_TRANSPORT=gmail  the Gmail API with an OAuth refresh token (see docs/outreach.md).
"""
import smtplib

from django.conf import settings

from . import gmail, resend_client, smtp_client
from .mime import new_message_id  # noqa: F401  # pylint: disable=unused-import

ERRORS = (gmail.GmailError, smtp_client.SmtpError, resend_client.ResendError, smtplib.SMTPException, OSError)


CLIENTS = {'gmail': gmail, 'resend': resend_client, 'smtp': smtp_client}


def transport():
    return settings.OUTREACH_TRANSPORT if settings.OUTREACH_TRANSPORT in CLIENTS else 'smtp'


def client():
    return CLIENTS[transport()]


def is_configured():
    return client().is_configured()


def send_message(to_email, subject, body, list_unsubscribe=True, **extra):
    """Returns (provider_message_id, provider_thread_id). Raises one of ERRORS."""
    return client().send_message(to_email, subject, body, list_unsubscribe=list_unsubscribe, **extra)
