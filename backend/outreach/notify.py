"""Email the owner every new draft so it can be reviewed before anything is sent."""
import logging

from django.conf import settings
from django.core import signing
from django.urls import reverse
from django.utils import timezone

from . import humanizer, mailer
from .services import final_body, preflight

logger = logging.getLogger(__name__)

SALT = 'outreach-review'


def make_review_token(message):
    return signing.dumps({'id': message.pk}, salt=SALT)


def read_review_token(token):
    """Return the message id, or raise signing.BadSignature / SignatureExpired."""
    max_age = settings.OUTREACH_REVIEW_LINK_DAYS * 24 * 3600
    return signing.loads(token, salt=SALT, max_age=max_age)['id']


def review_url(message):
    path = reverse('outreach-review', args=[make_review_token(message)])
    return f"{settings.OUTREACH_REVIEW_BASE_URL}{path}"


def build_notification(message):
    findings = humanizer.check(message.subject, message.body)
    problems = preflight(message)
    lines = [
        "A new outreach draft is waiting for your approval. Nothing is sent until you approve it.",
        "",
        f"To:      {message.to_email}",
        f"Subject: {message.subject}",
        "",
        "----- email as the recipient will see it -----",
        final_body(message.body),
        "----------------------------------------------",
        "",
    ]
    if problems:
        lines.append("Must fix before it can be approved:")
        lines.extend(f"  - {p}" for p in problems)
    else:
        lines.append("Safety and humanizer checks: passed.")
    tips = humanizer.warnings(findings)
    if tips:
        lines.append("")
        lines.append("Humanizer suggestions:")
        lines.extend(f"  - {t}" for t in tips)
    lines += [
        "",
        "Review, edit, approve or reject:",
        review_url(message),
        "",
        f"(The link works on the PC running LeadGen and expires in {settings.OUTREACH_REVIEW_LINK_DAYS} days.)",
    ]
    subject = f"[Review needed] {message.to_email}: {message.subject}"[:200]
    return subject, "\n".join(lines)


def notify_draft(message):
    """Send the review email. Returns a short status string."""
    if not settings.OUTREACH_NOTIFY_ON_DRAFT:
        return 'disabled'
    if not mailer.is_configured() or not settings.OUTREACH_NOTIFY_EMAIL:
        logger.warning("Draft %s created but no mailbox is configured; no review email sent.", message.pk)
        return f'{mailer.transport()}-not-configured'
    subject, body = build_notification(message)
    try:
        mailer.send_message(settings.OUTREACH_NOTIFY_EMAIL, subject, body, list_unsubscribe=False)
    except mailer.ERRORS as exc:
        logger.exception("Review email for draft %s failed", message.pk)
        message.notify_error = str(exc)[:500]
        message.save(update_fields=['notify_error', 'updated_at'])
        return 'failed'
    message.notified_at = timezone.now()
    message.notify_error = ''
    message.save(update_fields=['notified_at', 'notify_error', 'updated_at'])
    return 'sent'
