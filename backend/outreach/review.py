"""Review page opened from the "new draft" email: edit, approve or reject."""
from django.core import signing
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from . import batches, humanizer
from .models import OutreachBatch, OutreachMessage
from .notify import read_review_token
from .services import final_body, preflight


def _render(request, message, notice=None, ok=True, status=200):
    findings = humanizer.check(message.subject, message.body)
    return render(request, 'outreach/review.html', {
        'message': message,
        'preview': final_body(message.body),
        'problems': preflight(message) if message.status == OutreachMessage.Status.DRAFT else [],
        'tips': humanizer.warnings(findings),
        'words': len(message.body.split()),
        'editable': message.status == OutreachMessage.Status.DRAFT,
        'notice': notice,
        'ok': ok,
    }, status=status)


# The signed, expiring token in the URL is the credential (it only reaches your
# own inbox), so the form posts without a CSRF cookie.
@csrf_exempt
@require_http_methods(['GET', 'POST'])
def review_draft(request, token):
    try:
        message_id = read_review_token(token)
    except signing.SignatureExpired:
        return render(request, 'outreach/review.html', {'fatal': 'This review link has expired. Open the draft from the dashboard instead.'}, status=410)
    except signing.BadSignature:
        return render(request, 'outreach/review.html', {'fatal': 'This review link is not valid.'}, status=404)

    message = OutreachMessage.objects.filter(pk=message_id).select_related('lead').first()
    if message is None:
        return render(request, 'outreach/review.html', {'fatal': 'This draft no longer exists.'}, status=404)
    if request.method == 'GET':
        return _render(request, message)

    action = request.POST.get('action')
    if message.status != OutreachMessage.Status.DRAFT:
        return _render(request, message, f'This email is already {message.get_status_display().lower()}.', ok=False, status=409)

    if action == 'reject':
        message.status = OutreachMessage.Status.CANCELLED
        message.skip_reason = 'Rejected in review.'
        message.save(update_fields=['status', 'skip_reason', 'updated_at'])
        return _render(request, message, 'Rejected. This email will not be sent.')

    subject = request.POST.get('subject', message.subject).strip()[:200]
    body = request.POST.get('body', message.body).replace('\r\n', '\n').strip()
    if (subject, body) != (message.subject, message.body):
        message.subject, message.body = subject, body
        message.save(update_fields=['subject', 'body', 'updated_at'])

    if action == 'approve':
        problems = preflight(message)
        if problems:
            return _render(request, message, 'Not approved yet. Fix the items below, then approve again.', ok=False, status=400)
        message.status = OutreachMessage.Status.QUEUED
        message.approved_at = timezone.now()
        message.save(update_fields=['status', 'approved_at', 'updated_at'])
        return _render(request, message, 'Approved. It will send within your limits and send window.')
    return _render(request, message, 'Changes saved. Still a draft until you approve it.')


# --- batch review ---------------------------------------------------------------

def _batch_items(batch):
    items = []
    for message in batch.messages.select_related('lead').order_by('id'):
        is_draft = message.status == OutreachMessage.Status.DRAFT
        items.append({
            'message': message,
            'problems': preflight(message) if is_draft else [],
            'tips': [f['message'] for f in humanizer.check(message.subject, message.body)] if is_draft else [],
        })
    return items


def _render_batch(request, batch, notice=None, ok=True, status=200):
    return render(request, 'outreach/batch_review.html', {
        'batch': batch, 'items': _batch_items(batch), 'notice': notice, 'ok': ok,
        'editable': batch.status == OutreachBatch.Status.PENDING,
    }, status=status)


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def review_batch(request, token):
    try:
        batch_id = batches.read_batch_token(token)
    except signing.SignatureExpired:
        return render(request, 'outreach/batch_review.html', {'fatal': 'This review link has expired. Open the batch from the dashboard instead.'}, status=410)
    except signing.BadSignature:
        return render(request, 'outreach/batch_review.html', {'fatal': 'This review link is not valid.'}, status=404)
    batch = OutreachBatch.objects.filter(pk=batch_id).first()
    if batch is None:
        return render(request, 'outreach/batch_review.html', {'fatal': 'This batch no longer exists.'}, status=404)
    if request.method == 'GET':
        return _render_batch(request, batch)

    if batch.status != OutreachBatch.Status.PENDING:
        return _render_batch(request, batch, f'Already decided: {batch.get_status_display().lower()}.', ok=False, status=409)

    if request.POST.get('action') == 'reject':
        batches.reject_batch(batch.pk)
        batch.refresh_from_db()
        return _render_batch(request, batch, 'Rejected. Nothing will be sent.')

    ids = list(batch.messages.filter(status=OutreachMessage.Status.DRAFT).values_list('pk', flat=True))
    included = {int(i) for i in request.POST.getlist('include') if i.isdigit()}
    edits = {}
    for pk in ids:
        subject = request.POST.get(f'subject_{pk}')
        body = request.POST.get(f'body_{pk}')
        if subject is not None and body is not None:
            edits[pk] = (subject.strip()[:200], body.replace('\r\n', '\n').strip())
    outcome = batches.approve_batch(batch.pk, edits=edits, excluded={pk for pk in ids if pk not in included})
    if outcome is None:
        return _render_batch(request, batch, 'Someone already decided this batch.', ok=False, status=409)
    batch.refresh_from_db()
    return _render_batch(request, batch, batch.summary, ok=not outcome[3])
