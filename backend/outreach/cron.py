"""Scheduler entry point for hosts without background workers (Vercel).

A GitHub Actions workflow (or any cron service) calls this every 5 minutes with
`Authorization: Bearer $CRON_SECRET`. Each call does what Celery Beat did: send at most one due
email, batch quiet drafts, read the inbox / queue follow-ups, and send the Sunday report.
The slower autopilot (lead hunting + Gemini drafts) has its own endpoint so it never delays sending.
"""
import hmac
import logging

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .autopilot import run_autopilot
from .batches import process_batches
from .followups import schedule_followups
from .report import weekly_report
from .services import process_queue

logger = logging.getLogger(__name__)


def _authorised(request):
    secret = settings.CRON_SECRET
    if not secret:
        return None
    header = request.headers.get('Authorization', '')
    return hmac.compare_digest(header.encode(), f'Bearer {secret}'.encode())


def _run(request, jobs):
    ok = _authorised(request)
    if ok is None:
        return JsonResponse({'error': 'CRON_SECRET is not configured.'}, status=503)
    if not ok:
        return JsonResponse({'error': 'Unauthorized.'}, status=401)
    results = {}
    for name, job in jobs:
        try:
            results[name] = str(job())[:200]
        except Exception:  # one failing job must not stop the others
            logger.exception('Cron job %s failed', name)
            results[name] = 'error'
    return JsonResponse(results)


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def tick(request):
    return _run(request, (('queue', process_queue), ('batches', process_batches),
                          ('followups', schedule_followups), ('report', weekly_report)))


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def autopilot(request):
    return _run(request, (('autopilot', run_autopilot),))
