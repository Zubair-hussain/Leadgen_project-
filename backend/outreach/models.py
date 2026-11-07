from django.conf import settings
from django.db import models
from django.utils import timezone

from leads.models import Lead


class OutreachBatch(models.Model):
    """A group of drafts the admin approves with ONE decision."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Waiting for your decision'
        APPROVED = 'approved', 'Approved by you'
        AUTO_APPROVED = 'auto_approved', 'Auto-approved (no reply)'
        REJECTED = 'rejected', 'Rejected'
        HELD = 'held', 'Held (not sure, nothing auto-sent)'

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='outreach_batches',
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(default=timezone.now)
    notified_at = models.DateTimeField(null=True, blank=True)
    notify_error = models.CharField(max_length=500, blank=True)
    auto_send_at = models.DateTimeField(null=True, blank=True, help_text="If still pending after this, the auto-send policy runs")
    decided_at = models.DateTimeField(null=True, blank=True)
    summary = models.TextField(blank=True, help_text="What was approved, held or rejected, and why")

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'outreach batches'

    def __str__(self):
        return f"Batch {self.pk} [{self.status}]"


class LeadResearch(models.Model):
    """Fresh facts about a lead's business from SerpAPI (Google Maps), refreshed on a schedule."""

    class Status(models.TextChoices):
        OK = 'ok', 'Matched'
        CLOSED = 'closed', 'Business appears closed'
        NO_MATCH = 'no_match', 'No confident match'
        ERROR = 'error', 'Lookup failed'

    lead = models.OneToOneField(Lead, on_delete=models.CASCADE, related_name='research')
    status = models.CharField(max_length=20, choices=Status.choices)
    data = models.JSONField(default=dict, blank=True)
    note = models.CharField(max_length=300, blank=True)
    checked_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name_plural = 'lead research'

    def __str__(self):
        return f"{self.lead_id}: {self.status}"


class OutreachMessage(models.Model):
    """One personalised email to one lead, gated by human approval."""

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        QUEUED = 'queued', 'Approved & queued'
        SENDING = 'sending', 'Sending'
        SENT = 'sent', 'Sent'
        SKIPPED = 'skipped', 'Skipped by safety check'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='outreach_messages',
    )
    batch = models.ForeignKey(
        OutreachBatch,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='messages',
    )
    lead = models.ForeignKey(
        Lead,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='outreach_messages',
    )
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='followups',
        help_text="The first email of the thread, when this is a follow-up",
    )
    sequence_step = models.PositiveSmallIntegerField(default=0, help_text="0 = first email, 1+ = follow-up number")
    priority = models.SmallIntegerField(default=0, help_text="Higher is sent first (see outreach/playbook.py)")
    to_email = models.EmailField()
    subject = models.CharField(max_length=200)
    body = models.TextField(help_text="Plain-text body. The opt-out line is appended at send time.")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    skip_reason = models.CharField(max_length=255, blank=True)
    auto_approved = models.BooleanField(default=False, help_text="Queued by the auto-send policy, not by a person")
    hold_reason = models.CharField(max_length=500, blank=True, help_text="Why auto-send refused to send this one")
    error = models.TextField(blank=True)
    gmail_message_id = models.CharField(max_length=255, blank=True)
    gmail_thread_id = models.CharField(max_length=255, blank=True)
    rfc_message_id = models.CharField(max_length=255, blank=True, db_index=True,
                                      help_text="Message-ID header, used to thread follow-ups and match replies")
    replied_at = models.DateTimeField(null=True, blank=True, help_text="Set on the first email when the lead replies")
    bounced_at = models.DateTimeField(null=True, blank=True)
    dry_run = models.BooleanField(default=False, help_text="Sent while OUTREACH_DRY_RUN was on (nothing left the machine)")
    notified_at = models.DateTimeField(null=True, blank=True, help_text="When the review email was sent to you")
    notify_error = models.CharField(max_length=500, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', 'status']),
            models.Index(fields=['to_email', 'status']),
            models.Index(fields=['status', 'approved_at']),
            models.Index(fields=['sent_at']),
        ]

    def __str__(self):
        return f"{self.to_email} [{self.status}] {self.subject}"

    @property
    def root(self):
        return self.parent if self.parent_id else self

    def thread(self):
        """Every message in this conversation, oldest first."""
        root = self.root
        return OutreachMessage.objects.filter(models.Q(pk=root.pk) | models.Q(parent=root)).order_by('sequence_step', 'id')


class Suppression(models.Model):
    """Addresses that must never be emailed again by this owner."""

    class Reason(models.TextChoices):
        OPT_OUT = 'opt_out', 'Opted out'
        BOUNCE = 'bounce', 'Bounced'
        COMPLAINT = 'complaint', 'Spam complaint'
        MANUAL = 'manual', 'Added manually'

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='suppressions',
    )
    email = models.EmailField()
    reason = models.CharField(max_length=20, choices=Reason.choices, default=Reason.MANUAL)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['owner', 'email'], name='unique_suppression_per_owner'),
        ]

    def save(self, *args, **kwargs):
        self.email = (self.email or '').strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.email} ({self.reason})"


class SendThrottle(models.Model):
    """Single row tracking when the shared sending mailbox may send next."""

    key = models.CharField(max_length=50, unique=True, default='gmail')
    next_send_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.key}: next send after {self.next_send_at.isoformat()}"
