"""Polite persistence: queue the next follow-up for every thread that has gone quiet.

A follow-up is only created when the previous email in the thread was actually sent,
the lead has not replied or bounced, and the address is not suppressed. The inbox is
checked first, every time, so nobody who already answered gets a "bumping this up".
Follow-ups go through the same queue, limits, send window and safety checks as
first emails.
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from . import inbox, playbook
from .models import OutreachMessage, Suppression
from .services import normalize

logger = logging.getLogger(__name__)
Status = OutreachMessage.Status


def schedule_followups(now=None):
    """Returns {'inbox': <sync result>, 'queued': n}."""
    now = now or timezone.now()
    days = playbook.followup_days()
    if not settings.OUTREACH_FOLLOWUPS_ENABLED or not days:
        return {'inbox': None, 'queued': 0}
    synced = inbox.sync(now)

    oldest = now - timedelta(days=sum(days) + 30)
    roots = (OutreachMessage.objects
             .filter(parent__isnull=True, status=Status.SENT, sent_at__gte=oldest,
                     replied_at__isnull=True, bounced_at__isnull=True)
             .select_related('lead', 'owner'))
    queued = 0
    for root in roots:
        last = list(root.thread())[-1]
        if last.status != Status.SENT:
            continue  # a follow-up is pending, or the last one failed/was skipped: wait or stop
        step = last.sequence_step + 1
        if not playbook.followup_due(last, step, now):
            continue
        if Suppression.objects.filter(owner=root.owner, email=normalize(root.to_email)).exists():
            continue
        subject, body = playbook.followup_text(root, step)
        message = OutreachMessage(
            owner=root.owner, lead=root.lead, parent=root, sequence_step=step, to_email=root.to_email,
            subject=subject, body=body, status=Status.QUEUED, approved_at=now, auto_approved=root.auto_approved,
        )
        message.priority = playbook.priority(message)
        message.save()
        queued += 1
        logger.info("Queued follow-up %s for %s", step, root.to_email)
    return {'inbox': synced, 'queued': queued}
