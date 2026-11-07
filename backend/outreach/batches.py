"""Batch review: many drafts, one email to the admin, one decision.

If the admin has not answered by `auto_send_at`, the auto-send policy runs. It is
deliberately strict: a draft is only queued when EVERY check is certain. Anything
doubtful stays a draft and is reported to the admin instead.
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from . import ai, humanizer, mailer, playbook, research
from .models import OutreachBatch, OutreachMessage
from .services import final_body, mark_queued, normalize, preflight

logger = logging.getLogger(__name__)

SALT = 'outreach-batch-review'
Status = OutreachMessage.Status


def make_batch_token(batch):
    return signing.dumps({'batch': batch.pk}, salt=SALT)


def read_batch_token(token):
    max_age = settings.OUTREACH_REVIEW_LINK_DAYS * 24 * 3600
    return signing.loads(token, salt=SALT, max_age=max_age)['batch']


def batch_url(batch):
    return f"{settings.OUTREACH_REVIEW_BASE_URL}{reverse('outreach-batch-review', args=[make_batch_token(batch)])}"


# --- creating batches ---------------------------------------------------------

def cancel_duplicate_drafts(owner):
    """One business must never get two emails. Cancel older drafts for an address that already has a
    newer draft, or that is already queued/sending/sent. Returns how many were cancelled."""
    drafts = list(OutreachMessage.objects.filter(owner=owner, status=Status.DRAFT).order_by('-id'))
    taken = {normalize(m.to_email) for m in OutreachMessage.objects.filter(
        owner=owner, status__in=[Status.QUEUED, Status.SENDING]) | OutreachMessage.objects.filter(
        owner=owner, status=Status.SENT, dry_run=False)}
    cancelled = 0
    for draft in drafts:  # newest first, so the newest draft for an address wins
        address = normalize(draft.to_email)
        if address in taken:
            OutreachMessage.objects.filter(pk=draft.pk).update(
                status=Status.CANCELLED, skip_reason='Duplicate: this address already has another email.')
            cancelled += 1
        else:
            taken.add(address)
    return cancelled


def create_batch(owner, now=None):
    """Put all of the owner's un-batched drafts into one new batch and email the admin once."""
    now = now or timezone.now()
    cancel_duplicate_drafts(owner)
    drafts = list(OutreachMessage.objects.filter(
        owner=owner, status=Status.DRAFT, batch__isnull=True,
    ).order_by('id')[:settings.OUTREACH_BATCH_MAX])
    if not drafts:
        return None
    batch = OutreachBatch.objects.create(
        owner=owner,
        auto_send_at=(now + timedelta(hours=settings.OUTREACH_AUTO_SEND_AFTER_HOURS)
                      if settings.OUTREACH_AUTO_SEND_ENABLED else None),
    )
    OutreachMessage.objects.filter(pk__in=[d.pk for d in drafts]).update(batch=batch)
    notify_batch(batch)
    return batch


def create_pending_batches(now=None):
    """Batch every owner whose newest un-batched draft has been quiet for a moment."""
    now = now or timezone.now()
    quiet_before = now - timedelta(seconds=settings.OUTREACH_BATCH_QUIET_SECONDS)
    owners = (OutreachMessage.objects.filter(status=Status.DRAFT, batch__isnull=True)
              .values_list('owner_id', flat=True).distinct())
    created = []
    for owner_id in owners:
        newest = (OutreachMessage.objects.filter(owner_id=owner_id, status=Status.DRAFT, batch__isnull=True)
                  .order_by('-created_at').first())
        if newest and newest.created_at <= quiet_before:
            batch = create_batch(newest.owner, now)
            if batch:
                created.append(batch)
    return created


# --- emails to the admin ------------------------------------------------------

def _send_admin_email(subject, body):
    if not mailer.is_configured() or not settings.OUTREACH_NOTIFY_EMAIL:
        return f'{mailer.transport()}-not-configured'
    try:
        mailer.send_message(settings.OUTREACH_NOTIFY_EMAIL, subject[:200], body, list_unsubscribe=False)
    except mailer.ERRORS as exc:
        logger.exception("Admin email failed")
        return f'failed: {str(exc)[:300]}'
    return 'sent'


def build_batch_notification(batch):
    messages = list(batch.messages.filter(status=Status.DRAFT).select_related('lead'))
    lines = [f"{len(messages)} outreach email(s) are waiting for ONE decision from you. Nothing is sent until then.", ""]
    for index, message in enumerate(messages, 1):
        problems = preflight(message)
        tips = humanizer.check(message.subject, message.body)
        status = 'needs fixing: ' + problems[0] if problems else ('has suggestions' if tips else 'checks passed')
        preview = final_body(message.body)
        found = research.LeadResearch.objects.filter(lead_id=message.lead_id).first() if message.lead_id else None
        graded = playbook.score_message(message)
        grade = f"   Playbook score {graded['score']}/100" + (f": {graded['notes'][0]}" if graded['notes'] else '')
        lines += [f"{index}. To: {message.to_email}  [{status}]", f"   {research.summary_line(found)}", grade,
                  f"   Subject: {message.subject}",
                  "   " + preview[:500].replace("\n", "\n   ") + ("..." if len(preview) > 500 else ""), ""]
    lines += ["Review and approve all, drop individual emails, or reject everything:", batch_url(batch), ""]
    if batch.auto_send_at:
        lines += [
            f"If you do not answer by {timezone.localtime(batch.auto_send_at):%a %d %b %H:%M %Z}, the auto-send policy runs.",
            "It only sends an email when EVERY check is certain (safety checks, humanizer, business address,",
            "and Gemini's confident approval). Anything uncertain is held back and you are told why.",
        ]
    else:
        lines.append("Auto-send is off: nothing is sent unless you approve it.")
    return f"[Review needed] {len(messages)} outreach email(s), one approval", "\n".join(lines)


def notify_batch(batch):
    subject, body = build_batch_notification(batch)
    result = _send_admin_email(subject, body)
    if result == 'sent':
        batch.notified_at, batch.notify_error = timezone.now(), ''
    else:
        batch.notify_error = result[:500]
    batch.save(update_fields=['notified_at', 'notify_error'])
    return result


# --- decisions ------------------------------------------------------------------

def _claim(batch_id, new_status):
    """Atomically move a PENDING batch to new_status. Returns the batch or None if someone else decided."""
    with transaction.atomic():
        batch = OutreachBatch.objects.select_for_update().filter(pk=batch_id).first()
        if batch is None or batch.status != OutreachBatch.Status.PENDING:
            return None
        batch.status = new_status
        batch.decided_at = timezone.now()
        batch.save(update_fields=['status', 'decided_at'])
        return batch


def approve_batch(batch_id, edits=None, excluded=()):
    """Admin approval. edits = {message_id: (subject, body)}. Returns (batch, queued, rejected, problems) or None."""
    batch = _claim(batch_id, OutreachBatch.Status.APPROVED)
    if batch is None:
        return None
    edits, now = edits or {}, timezone.now()
    queued, dropped, problems = 0, 0, []
    for message in batch.messages.filter(status=Status.DRAFT).select_related('lead'):
        if message.pk in excluded:
            message.status, message.skip_reason = Status.CANCELLED, 'Excluded in review.'
            message.save(update_fields=['status', 'skip_reason', 'updated_at'])
            dropped += 1
            continue
        if message.pk in edits:
            message.subject, message.body = edits[message.pk]
            message.save(update_fields=['subject', 'body', 'updated_at'])
        found = preflight(message)
        if found:
            message.skip_reason = found[0][:255]
            message.save(update_fields=['skip_reason', 'updated_at'])
            problems.append(f"{message.to_email}: {found[0]}")
            continue
        mark_queued(message, now)
        queued += 1
    batch.summary = (f"You approved {queued} email(s); {dropped} dropped; {len(problems)} blocked by checks."
                     + ''.join(f"\n- {p}" for p in problems))
    batch.save(update_fields=['summary'])
    return batch, queued, dropped, problems


def reject_batch(batch_id):
    batch = _claim(batch_id, OutreachBatch.Status.REJECTED)
    if batch is None:
        return None
    count = batch.messages.filter(status=Status.DRAFT).update(
        status=Status.CANCELLED, skip_reason='Rejected in review.')
    batch.summary = f"You rejected the batch. {count} email(s) cancelled."
    batch.save(update_fields=['summary'])
    return batch


# --- auto-send policy -------------------------------------------------------------

def unsure_reason(message):
    """Return why this draft must NOT be auto-sent, or '' only when every check is certain."""
    found = preflight(message)
    if found:
        return found[0]
    if humanizer.check(message.subject, message.body):
        return 'Humanizer check has findings, so a person should read it first.'
    domain = normalize(message.to_email).rsplit('@', 1)[-1]
    if domain in settings.OUTREACH_FREEMAIL_DOMAINS:
        return f'{domain} is a personal mailbox, which needs consent. Auto-send is for business domains only.'
    if len(message.body.split()) > settings.OUTREACH_MAX_WORDS:
        return 'Email is longer than the word limit.'
    graded = playbook.score_message(message)
    if graded['score'] < settings.OUTREACH_MIN_PLAYBOOK_SCORE:
        return (f"Playbook score {graded['score']} is below {settings.OUTREACH_MIN_PLAYBOOK_SCORE}: "
                + '; '.join(graded['notes']))
    if message.lead_id and settings.OUTREACH_RESEARCH_ENABLED:
        found = research.get_research(message.lead)
        if found is None or found.status != research.Status.OK:
            return f"Business could not be confirmed on Google Maps ({found.note if found else 'no lookup'})."
    approved, reason = ai.review_email(message)
    return '' if approved else reason


def auto_approve_batch(batch_id):
    """Run the policy for a batch the admin never answered. Returns the batch or None."""
    batch = _claim(batch_id, OutreachBatch.Status.HELD)
    if batch is None:
        return None
    now, queued, held = timezone.now(), [], []
    for message in batch.messages.filter(status=Status.DRAFT).select_related('lead'):
        reason = unsure_reason(message)
        if reason:
            message.hold_reason = reason[:500]
            message.save(update_fields=['hold_reason', 'updated_at'])
            held.append(message)
        else:
            mark_queued(message, now, auto=True)
            queued.append(message)
    batch.status = OutreachBatch.Status.AUTO_APPROVED if queued else OutreachBatch.Status.HELD
    lines = [f"No reply by the deadline, so the auto-send policy ran: {len(queued)} queued, {len(held)} held back."]
    lines += [f"- SENDING: {m.to_email}" for m in queued]
    lines += [f"- HELD: {m.to_email}: {m.hold_reason}" for m in held]
    batch.summary = "\n".join(lines)
    batch.save(update_fields=['status', 'summary'])
    _send_admin_email(f"[Auto-send] {len(queued)} queued, {len(held)} held back",
                      batch.summary + (f"\n\nReview the held ones here:\n{batch_url(batch)}" if held else ''))
    return batch


def run_auto_sends(now=None):
    """Auto-send overdue batches. Only batches the admin was actually notified about qualify."""
    if not settings.OUTREACH_AUTO_SEND_ENABLED:
        return []
    now = now or timezone.now()
    due = OutreachBatch.objects.filter(
        status=OutreachBatch.Status.PENDING, auto_send_at__lte=now, notified_at__isnull=False,
    ).values_list('pk', flat=True)
    return [b for b in (auto_approve_batch(pk) for pk in due) if b]


def process_batches(now=None):
    return {'created': len(create_pending_batches(now)), 'auto': len(run_auto_sends(now))}
