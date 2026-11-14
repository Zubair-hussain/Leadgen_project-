"""Weekly report: every Sunday evening, email yourself what the machine did in the last 7 days."""
import logging
import zoneinfo
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from leads.models import Lead

from . import mailer
from .models import OutreachMessage, SendThrottle, Suppression

logger = logging.getLogger(__name__)
Status = OutreachMessage.Status

REPORT_KEY = 'weekly-report'
DAY_NAMES = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')


def report_zone():
    try:
        return zoneinfo.ZoneInfo(settings.OUTREACH_REPORT_TIMEZONE)
    except (zoneinfo.ZoneInfoNotFoundError, ValueError):
        return zoneinfo.ZoneInfo('UTC')


def is_due(now):
    local = timezone.localtime(now, report_zone())
    return local.weekday() == settings.OUTREACH_REPORT_WEEKDAY and local.hour >= settings.OUTREACH_REPORT_HOUR


def collect(now):
    """Numbers for the 7 days ending at `now`."""
    start = now - timedelta(days=7)
    messages = OutreachMessage.objects.all()
    real = messages.filter(status=Status.SENT, dry_run=False, sent_at__gte=start, sent_at__lt=now)
    first = real.filter(parent__isnull=True)
    zone = report_zone()
    per_day = {}
    for sent_at in real.values_list('sent_at', flat=True):
        day = timezone.localtime(sent_at, zone).date()
        per_day[day] = per_day.get(day, 0) + 1
    days = [(timezone.localtime(now, zone) - timedelta(days=i)).date() for i in range(6, -1, -1)]
    replies = messages.filter(parent__isnull=True, replied_at__gte=start, replied_at__lt=now).count()
    stats = {
        'start': start,
        'end': now,
        'leads_found': Lead.objects.filter(created_at__gte=start, created_at__lt=now).count(),
        'drafts_written': messages.filter(parent__isnull=True, created_at__gte=start, created_at__lt=now)
                                  .exclude(status=Status.CANCELLED).count(),
        'sent_total': real.count(),
        'sent_first': first.count(),
        'sent_followups': real.filter(parent__isnull=False).count(),
        'dry_run': messages.filter(status=Status.SENT, dry_run=True, sent_at__gte=start, sent_at__lt=now).count(),
        'auto_approved': real.filter(auto_approved=True).count(),
        'replies': replies,
        'bounces': messages.filter(parent__isnull=True, bounced_at__gte=start, bounced_at__lt=now).count(),
        'opt_outs': Suppression.objects.filter(created_at__gte=start, created_at__lt=now,
                                               reason=Suppression.Reason.OPT_OUT).count(),
        'complaints': Suppression.objects.filter(created_at__gte=start, created_at__lt=now,
                                                 reason=Suppression.Reason.COMPLAINT).count(),
        'skipped': messages.filter(status=Status.SKIPPED, updated_at__gte=start, updated_at__lt=now).count(),
        'failed': messages.filter(status=Status.FAILED, updated_at__gte=start, updated_at__lt=now).count(),
        'waiting': messages.filter(status__in=(Status.DRAFT, Status.QUEUED)).count(),
        'per_day': [(day, per_day.get(day, 0)) for day in days],
        'all_time_sent': messages.filter(status=Status.SENT, dry_run=False).count(),
    }
    stats['reply_rate'] = round(100 * replies / stats['sent_first'], 1) if stats['sent_first'] else 0.0
    stats['bounce_rate'] = round(100 * stats['bounces'] / stats['sent_first'], 1) if stats['sent_first'] else 0.0
    return stats


def health_notes(stats):
    notes = []
    if stats['sent_first'] and stats['bounce_rate'] > 3:
        notes.append(f"Bounce rate is {stats['bounce_rate']}%. Keep it under 2%: verify leads before sending.")
    if stats['complaints']:
        notes.append(f"{stats['complaints']} spam complaint(s). Pause and rewrite the emails before sending more.")
    if stats['failed']:
        notes.append(f"{stats['failed']} email(s) failed to send. Check the Outreach page for the error.")
    if not stats['sent_total'] and stats['dry_run']:
        notes.append('Dry run is ON, so nothing really left. Set OUTREACH_DRY_RUN=False to go live.')
    if not stats['sent_total'] and not stats['dry_run'] and not stats['waiting']:
        notes.append('Nothing was sent and nothing is waiting. Check the autopilot targets and API keys.')
    return notes


def build(stats):
    fmt = '%a %d %b'
    zone = report_zone()
    period = (f"{timezone.localtime(stats['start'], zone).strftime(fmt)} to "
              f"{timezone.localtime(stats['end'], zone).strftime(fmt)}")
    subject = f"Weekly outreach report: {stats['sent_total']} emails sent ({period})"
    lines = [
        f'Your LeadGen week, {period}.',
        '',
        f"Emails sent:        {stats['sent_total']}  ({stats['sent_first']} first emails, "
        f"{stats['sent_followups']} follow-ups)",
        f"Replies:            {stats['replies']}  ({stats['reply_rate']}% of first emails)",
        f"New leads found:    {stats['leads_found']}",
        f"Drafts written:     {stats['drafts_written']}",
        f"Auto-approved sent: {stats['auto_approved']}",
        f"Bounces:            {stats['bounces']}  ({stats['bounce_rate']}%)",
        f"Opt-outs:           {stats['opt_outs']}",
        f"Spam complaints:    {stats['complaints']}",
        f"Skipped by checks:  {stats['skipped']}",
        f"Failed:             {stats['failed']}",
        f"Waiting now:        {stats['waiting']} (drafts + queued)",
    ]
    if stats['dry_run']:
        lines.append(f"Dry-run (not sent):  {stats['dry_run']}")
    lines += ['', 'Sent per day:']
    lines += [f"  {DAY_NAMES[day.weekday()]} {day.strftime('%d %b')}: {count}" for day, count in stats['per_day']]
    lines += ['', f"All-time emails sent: {stats['all_time_sent']}"]
    notes = health_notes(stats)
    if notes:
        lines += ['', 'Worth a look:'] + [f'  - {n}' for n in notes]
    return subject, '\n'.join(lines)


def _move_marker(now, delta):
    with transaction.atomic():
        marker, _ = SendThrottle.objects.select_for_update().get_or_create(
            key=REPORT_KEY, defaults={'next_send_at': now - timedelta(days=1)})
        if marker.next_send_at > now:
            return False
        marker.next_send_at = now + delta
        marker.save(update_fields=['next_send_at'])
    return True


def send_report(now=None):
    """Build and email the report right now, whatever the day. Returns a status string."""
    now = now or timezone.now()
    if not mailer.is_configured() or not settings.OUTREACH_NOTIFY_EMAIL:
        return f'{mailer.transport()}-not-configured'
    subject, body = build(collect(now))
    try:
        mailer.send_message(settings.OUTREACH_NOTIFY_EMAIL, subject[:200], body, list_unsubscribe=False)
    except mailer.ERRORS as exc:
        logger.exception('Weekly report email failed')
        return f'failed: {str(exc)[:200]}'
    return 'sent'


def weekly_report(now=None):
    """Called by the scheduler every few minutes; sends once, on the report day after the report hour."""
    if not settings.OUTREACH_WEEKLY_REPORT_ENABLED:
        return 'disabled'
    now = now or timezone.now()
    if not is_due(now):
        return 'not-due'
    if not _move_marker(now, timedelta(days=6)):
        return 'already-sent'
    result = send_report(now)
    if result != 'sent':
        # Try again in an hour instead of waiting a week.
        SendThrottle.objects.filter(key=REPORT_KEY).update(next_send_at=now + timedelta(hours=1))
    return result
