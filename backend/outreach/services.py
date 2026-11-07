"""Safety checks, rate limiting and the send loop for outreach email."""
import logging
import random
import re
import zoneinfo
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from leads.services import EmailVerifier

from . import branding, compliance, humanizer, mailer, playbook, research
from .models import OutreachMessage, SendThrottle, Suppression

logger = logging.getLogger(__name__)

URL_RE = re.compile(r'https?://\S+', re.IGNORECASE)
FAKE_REPLY_RE = re.compile(r'^\s*(re|fwd?|fw)\s*:', re.IGNORECASE)
PENDING_STATUSES = (OutreachMessage.Status.QUEUED, OutreachMessage.Status.SENDING)


def normalize(email):
    return EmailVerifier.normalize_email(email)


def content_problems(subject, body, followup=False):
    """Rules from the outreach playbook: honest subject, few links, real content.

    A follow-up really is a reply in an existing thread, so its "Re:" is honest.
    """
    problems = []
    if not (subject or '').strip():
        problems.append("Subject is empty.")
    elif FAKE_REPLY_RE.match(subject) and not followup:
        problems.append("Subject must not start with Re:/Fwd: on a first email.")
    if not (body or '').strip():
        problems.append("Body is empty.")
    elif len(URL_RE.findall(body)) > settings.OUTREACH_MAX_LINKS:
        problems.append(f"Body has more than {settings.OUTREACH_MAX_LINKS} links.")
    if settings.OUTREACH_HUMANIZER_STRICT:
        problems.extend(humanizer.blocking(humanizer.check(subject, body)))
    return problems


def content_warnings(subject, body):
    findings = humanizer.check(subject, body)
    result = humanizer.warnings(findings)
    if not settings.OUTREACH_HUMANIZER_STRICT:
        result = humanizer.blocking(findings) + result
    words = len((body or '').split())
    if words > settings.OUTREACH_MAX_WORDS:
        result.append(f"Body is {words} words; aim for {settings.OUTREACH_MAX_WORDS} or fewer.")
    return result


def recipient_problems(message):
    """Return the first reason this recipient must not be emailed, or ''."""
    email = normalize(message.to_email)
    if not EmailVerifier.is_valid_syntax(email):
        return "Invalid email address."
    if Suppression.objects.filter(owner=message.owner, email=email).exists():
        return "Recipient is on the suppression list."
    if message.lead_id:
        if not message.lead.is_verified:
            return "Lead email is not verified yet (run Verify first)."
    elif not EmailVerifier.verify_domain(email):
        return "Recipient domain has no MX records."

    others = OutreachMessage.objects.filter(owner=message.owner, to_email__iexact=email).exclude(pk=message.pk)
    if message.parent_id:
        root = message.parent
        if root.replied_at:
            return "Lead already replied, so no follow-up."
        if root.bounced_at:
            return "First email bounced."
        # Earlier emails in this same thread are the conversation, not a re-contact.
        others = others.exclude(pk=root.pk).exclude(parent=root)
    cutoff = timezone.now() - timedelta(days=settings.OUTREACH_RECONTACT_DAYS)
    # Dry-run "sends" never left the machine, so they don't count as contact.
    if others.filter(status=OutreachMessage.Status.SENT, dry_run=False, sent_at__gte=cutoff).exists():
        return f"Already contacted in the last {settings.OUTREACH_RECONTACT_DAYS} days."
    if others.filter(status__in=PENDING_STATUSES).exists():
        return "Another email to this address is already queued."
    return ''


def preflight(message):
    """All blocking problems for a message, as a list of strings."""
    problems = content_problems(message.subject, message.body, followup=bool(message.parent_id))
    recipient = recipient_problems(message)
    if recipient:
        problems.append(recipient)
    legal = compliance.problems(message)
    if legal:
        problems.append(legal)
    return problems


def final_body(body):
    line = settings.OUTREACH_OPT_OUT_LINE.strip()
    return f"{body.rstrip()}\n\n{line}" if line else body


def mark_queued(message, now=None, auto=False):
    """Put an approved message in the send queue with its playbook priority."""
    message.status = OutreachMessage.Status.QUEUED
    message.approved_at = now or timezone.now()
    message.auto_approved = auto
    message.priority = playbook.priority(message)
    message.save(update_fields=['status', 'approved_at', 'auto_approved', 'priority', 'updated_at'])
    return message


def in_send_window(now=None, region=''):
    """Business hours (and weekdays) in the lead's own region, so Australia is emailed in its morning."""
    zone = zoneinfo.ZoneInfo(compliance.timezone_name(region)) if region else None
    local = timezone.localtime(now or timezone.now(), zone)
    if settings.OUTREACH_WEEKDAYS_ONLY and local.weekday() >= 5:
        return False
    return settings.OUTREACH_SEND_HOUR_START <= local.hour < settings.OUTREACH_SEND_HOUR_END


def sent_counts(now=None):
    now = now or timezone.now()
    day_start = timezone.localtime(now).replace(hour=0, minute=0, second=0, microsecond=0)
    sent = OutreachMessage.objects.filter(status=OutreachMessage.Status.SENT)
    return {
        'today': sent.filter(sent_at__gte=day_start).count(),
        'last_hour': sent.filter(sent_at__gte=now - timedelta(hours=1)).count(),
    }


def next_delay():
    low = settings.OUTREACH_MIN_DELAY_SECONDS
    high = max(low, settings.OUTREACH_MAX_DELAY_SECONDS)
    return timedelta(seconds=random.randint(low, high))


def queue_status():
    throttle = SendThrottle.objects.filter(key='gmail').first()
    counts = sent_counts()
    queued = OutreachMessage.objects.filter(status=OutreachMessage.Status.QUEUED)
    sent = OutreachMessage.objects.filter(status=OutreachMessage.Status.SENT, dry_run=False, parent__isnull=True)
    return {
        'transport': mailer.transport(),
        'mail_configured': mailer.is_configured(),
        'gmail_configured': mailer.is_configured(),  # older frontends read this key
        'dry_run': settings.OUTREACH_DRY_RUN,
        'from_email': settings.OUTREACH_FROM_EMAIL,
        'in_send_window': in_send_window(),
        'sent_today': counts['today'],
        'sent_last_hour': counts['last_hour'],
        'daily_limit': playbook.daily_limit(),
        'daily_limit_max': settings.OUTREACH_DAILY_LIMIT,
        'hourly_limit': settings.OUTREACH_HOURLY_LIMIT,
        'queued': queued.count(),
        'queued_followups': queued.filter(parent__isnull=False).count(),
        'threads_sent': sent.count(),
        'threads_replied': sent.filter(replied_at__isnull=False).count(),
        'next_send_at': throttle.next_send_at.isoformat() if throttle else None,
    }


def thread_headers(message):
    """In-Reply-To/References (and the Gmail thread) so a follow-up lands in the same conversation."""
    if not message.parent_id:
        return {}
    earlier = [m for m in message.thread() if m.pk != message.pk and m.status == OutreachMessage.Status.SENT]
    ids = [m.rfc_message_id for m in earlier if m.rfc_message_id]
    if not ids:
        return {'thread_id': message.parent.gmail_thread_id}
    return {'in_reply_to': ids[-1], 'references': ' '.join(ids), 'thread_id': message.parent.gmail_thread_id}


def process_queue(now=None):
    """Send at most one approved message, if every limit allows it.

    Called every minute by Celery Beat. Returns a short string describing
    what happened, which is handy in logs and the management command.
    """
    now = now or timezone.now()
    if not settings.OUTREACH_DRY_RUN and not mailer.is_configured():
        return f'{mailer.transport()}-not-configured'
    open_regions = [r for r in ('',) + compliance.REGIONS if in_send_window(now, r)]
    if not open_regions:
        return 'outside-send-window'

    with transaction.atomic():
        throttle, _ = SendThrottle.objects.select_for_update().get_or_create(
            key='gmail', defaults={'next_send_at': now - timedelta(days=1)},
        )
        if throttle.next_send_at > now:
            return 'waiting-for-delay'
        counts = sent_counts(now)
        if counts['today'] >= playbook.daily_limit(now):
            return 'daily-limit-reached'
        if counts['last_hour'] >= settings.OUTREACH_HOURLY_LIMIT:
            return 'hourly-limit-reached'

        queue = (
            OutreachMessage.objects.select_for_update()
            .filter(status=OutreachMessage.Status.QUEUED)
            .order_by('-priority', 'approved_at', 'id')
        )
        message = None
        for candidate in queue[:50]:
            if compliance.message_region(candidate) in open_regions:
                message = candidate
                break
        if message is None and queue.exists():
            return 'outside-send-window'
        if message is None:
            return 'queue-empty'

        message.status = OutreachMessage.Status.SENDING
        message.save(update_fields=['status', 'updated_at'])

        problems = preflight(message)
        if problems:
            message.status = OutreachMessage.Status.SKIPPED
            message.skip_reason = problems[0][:255]
            message.save(update_fields=['status', 'skip_reason', 'updated_at'])
            return 'skipped'

        blocker = research.send_blocker(message)
        if blocker:
            message.status = OutreachMessage.Status.SKIPPED
            message.skip_reason = blocker[:255]
            message.save(update_fields=['status', 'skip_reason', 'updated_at'])
            return 'skipped'

        message.rfc_message_id = mailer.new_message_id()
        try:
            if settings.OUTREACH_DRY_RUN:
                message_id, thread_id = f'dry-run-{message.pk}', ''
                logger.info("DRY RUN: would send %s to %s", message.pk, message.to_email)
            else:
                lead = message.lead
                text, html = branding.compose(
                    message.subject, message.body,
                    region=compliance.message_region(message), source=lead.source if lead else '')
                message_id, thread_id = mailer.send_message(
                    normalize(message.to_email), message.subject, text, html=html,
                    message_id=message.rfc_message_id, **thread_headers(message),
                )
        except mailer.ERRORS as exc:
            logger.exception("Outreach send failed for message %s", message.pk)
            message.status = OutreachMessage.Status.FAILED
            message.error = str(exc)[:2000]
            message.save(update_fields=['status', 'error', 'updated_at'])
            throttle.next_send_at = now + next_delay()
            throttle.save(update_fields=['next_send_at'])
            return 'failed'

        message.status = OutreachMessage.Status.SENT
        message.gmail_message_id = message_id
        message.gmail_thread_id = thread_id
        message.dry_run = settings.OUTREACH_DRY_RUN
        message.sent_at = now
        message.save(update_fields=[
            'status', 'gmail_message_id', 'gmail_thread_id', 'rfc_message_id', 'dry_run', 'sent_at', 'updated_at',
        ])
        throttle.next_send_at = now + next_delay()
        throttle.save(update_fields=['next_send_at'])
        return 'sent'
