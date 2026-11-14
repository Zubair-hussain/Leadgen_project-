"""Resend webhook: bounces and spam complaints are suppressed the moment they happen.

Protecting the sender reputation of a new domain matters more than anything else: mailing a
dead address again, or someone who pressed "spam", is what lands you in spam folders.
Resend signs webhooks with Svix; the signature is checked here without extra packages.
"""
import base64
import hashlib
import hmac
import json
import logging
import time

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import OutreachMessage, Suppression

logger = logging.getLogger(__name__)
TOLERANCE_SECONDS = 5 * 60


def verify_signature(secret, msg_id, timestamp, signature_header, body):
    if not (secret and msg_id and timestamp and signature_header):
        return False
    try:
        if abs(time.time() - int(timestamp)) > TOLERANCE_SECONDS:
            return False
        key = base64.b64decode(secret.split('_', 1)[1] if secret.startswith('whsec_') else secret)
    except (ValueError, TypeError):
        return False
    signed = f'{msg_id}.{timestamp}.'.encode() + body
    expected = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
    for part in signature_header.split():
        _, _, sig = part.partition(',')
        if sig and hmac.compare_digest(sig, expected):
            return True
    return False


def handle_event(event):
    kind = event.get('type', '')
    data = event.get('data') or {}
    reason = {'email.bounced': Suppression.Reason.BOUNCE,
              'email.complained': Suppression.Reason.COMPLAINT}.get(kind)
    if reason is None:
        return 'ignored'
    message = OutreachMessage.objects.filter(gmail_message_id=data.get('email_id', '')).select_related('parent').first()
    if message is None:
        return 'unknown-email'
    root = message.root
    if reason == Suppression.Reason.BOUNCE and root.bounced_at is None:
        root.bounced_at = timezone.now()
        root.save(update_fields=['bounced_at', 'updated_at'])
    Suppression.objects.get_or_create(
        owner=message.owner, email=message.to_email.strip().lower(),
        defaults={'reason': reason, 'note': f'Resend {kind}'[:255]})
    # Anything still waiting for this address is cancelled.
    OutreachMessage.objects.filter(
        owner=message.owner, to_email__iexact=message.to_email,
        status__in=(OutreachMessage.Status.DRAFT, OutreachMessage.Status.QUEUED),
    ).update(status=OutreachMessage.Status.CANCELLED, skip_reason=f'Suppressed after {kind}'[:255])
    return 'suppressed'


@csrf_exempt
@require_POST
def resend_webhook(request):
    secret = settings.RESEND_WEBHOOK_SECRET
    if not secret:
        return JsonResponse({'error': 'RESEND_WEBHOOK_SECRET is not configured.'}, status=503)
    ok = verify_signature(secret, request.headers.get('svix-id', ''), request.headers.get('svix-timestamp', ''),
                          request.headers.get('svix-signature', ''), request.body)
    if not ok:
        return JsonResponse({'error': 'Bad signature.'}, status=401)
    try:
        event = json.loads(request.body)
    except ValueError:
        return JsonResponse({'error': 'Bad JSON.'}, status=400)
    result = handle_event(event)
    logger.info('Resend webhook %s: %s', event.get('type'), result)
    return JsonResponse({'result': result})
