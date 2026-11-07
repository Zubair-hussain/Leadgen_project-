import logging

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from kombu.exceptions import OperationalError

from .models import OutreachMessage

logger = logging.getLogger(__name__)


def _queue_notification(message_id):
    from .tasks import notify_draft_created

    try:
        notify_draft_created.delay(message_id)
    except OperationalError:
        # Redis/Celery unavailable: send inline so the draft is never missed.
        logger.warning("Celery unavailable; sending review email for draft %s inline.", message_id)
        notify_draft_created(message_id)


@receiver(post_save, sender=OutreachMessage)
def notify_on_new_draft(sender, instance, created, **kwargs):  # pylint: disable=unused-argument
    """Every draft, however it was created (dashboard, API, AI writer), triggers a review email."""
    if settings.OUTREACH_BATCH_REVIEW:
        return  # drafts are grouped into one review email by outreach.batches
    if created and instance.status == OutreachMessage.Status.DRAFT:
        transaction.on_commit(lambda: _queue_notification(instance.pk))
