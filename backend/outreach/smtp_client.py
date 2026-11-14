"""Send through a normal mailbox over SMTP (Hostinger: smtp.hostinger.com, port 465, SSL).

After sending, a copy is saved to the mailbox's Sent folder over IMAP, because SMTP alone
does not do that and you want to see your outreach in Hostinger webmail. That copy is
best effort: a failure there never fails the send.
"""
import imaplib
import logging
import smtplib
import ssl
import time

from django.conf import settings

from .mime import build_mime

logger = logging.getLogger(__name__)


class SmtpError(Exception):
    """Raised when the SMTP server refuses to log in or to accept a message."""


def is_configured():
    return all([
        settings.OUTREACH_SMTP_HOST,
        settings.OUTREACH_SMTP_USER,
        settings.OUTREACH_SMTP_PASSWORD,
        settings.OUTREACH_FROM_EMAIL,
    ])


def connect():
    """Logged-in SMTP connection. SSL on 465, STARTTLS otherwise."""
    context = ssl.create_default_context()
    host, port = settings.OUTREACH_SMTP_HOST, settings.OUTREACH_SMTP_PORT
    try:
        if settings.OUTREACH_SMTP_SSL:
            server = smtplib.SMTP_SSL(host, port, context=context, timeout=30)
        else:
            server = smtplib.SMTP(host, port, timeout=30)
            server.starttls(context=context)
        server.login(settings.OUTREACH_SMTP_USER, settings.OUTREACH_SMTP_PASSWORD)
    except smtplib.SMTPAuthenticationError as exc:
        raise SmtpError(f"SMTP login refused for {settings.OUTREACH_SMTP_USER}: check the mailbox password.") from exc
    except smtplib.SMTPException as exc:
        raise SmtpError(f"SMTP connection failed: {exc}") from exc
    return server


def send_message(to_email, subject, body, list_unsubscribe=True, html=None, message_id=None,
                 in_reply_to='', references='', thread_id='', unsubscribe_url=''):  # pylint: disable=unused-argument
    """Send one email. Returns (message_id, '') to match the Gmail client's (id, thread) shape."""
    mime = build_mime(to_email, subject, body, list_unsubscribe=list_unsubscribe, html=html,
                      message_id=message_id, in_reply_to=in_reply_to, references=references,
                      unsubscribe_url=unsubscribe_url)
    server = connect()
    try:
        refused = server.send_message(mime)
    except smtplib.SMTPRecipientsRefused as exc:
        raise SmtpError(f"Recipient refused by the server: {to_email}") from exc
    except smtplib.SMTPException as exc:
        raise SmtpError(f"SMTP send failed: {exc}") from exc
    finally:
        try:
            server.quit()
        except smtplib.SMTPException:
            pass
    if refused:
        raise SmtpError(f"Recipient refused by the server: {', '.join(refused)}")
    logger.info("SMTP sent %s to %s", mime['Message-ID'], to_email)
    save_to_sent(mime)
    return mime['Message-ID'], ''


def save_to_sent(mime):
    if not settings.OUTREACH_IMAP_SAVE_SENT or not settings.OUTREACH_IMAP_HOST:
        return False
    from . import inbox

    try:
        with inbox.connect() as imap:
            folder = inbox.sent_folder(imap)
            imap.append(folder, r'(\Seen)', imaplib.Time2Internaldate(time.time()), mime.as_bytes())
    except (imaplib.IMAP4.error, OSError, inbox.InboxError) as exc:
        logger.warning("Sent, but could not save a copy to the Sent folder: %s", exc)
        return False
    return True
