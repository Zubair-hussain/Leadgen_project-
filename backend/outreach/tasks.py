from celery import shared_task

from .models import OutreachMessage
from .services import process_queue


@shared_task
def process_outreach_queue():
    """Runs every minute via Celery Beat; sends at most one approved email."""
    return process_queue()


@shared_task
def notify_draft_created(message_id):
    """Email the owner a review link for a new draft."""
    from .notify import notify_draft

    message = OutreachMessage.objects.filter(pk=message_id, status=OutreachMessage.Status.DRAFT).first()
    return notify_draft(message) if message else 'not-a-draft'


@shared_task
def process_followups():
    """Every few minutes: read the inbox for replies/bounces, then queue follow-ups that are due."""
    from .followups import schedule_followups

    return schedule_followups()


@shared_task
def process_batches():
    """Every minute: batch quiet drafts into ONE review email, and run the auto-send policy when due."""
    from .batches import process_batches as run

    return run()


@shared_task
def run_autopilot():
    """Every 30 minutes: hunt leads once a day, otherwise draft a couple of emails."""
    from .autopilot import run_autopilot as run

    return run()


@shared_task
def weekly_report():
    """Every 15 minutes: emails the weekly report once, on Sunday evening."""
    from .report import weekly_report as run

    return run()
