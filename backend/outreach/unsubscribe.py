"""One-click unsubscribe (RFC 8058), as Gmail, Yahoo and Outlook expect from senders.

Every email carries:
    List-Unsubscribe: <https://backend/api/outreach/unsubscribe/<token>/>, <mailto:reply-to?subject=unsubscribe>
    List-Unsubscribe-Post: List-Unsubscribe=One-Click
so the mail app can show its own "Unsubscribe" button. Pressing it POSTs here and the address is
suppressed at once. The same link is in the email footer (GET shows a confirm button, so link
scanners that only open URLs never unsubscribe anyone by accident).

The token never expires: CAN-SPAM requires opt-out to keep working for at least 30 days.
"""
from django.conf import settings
from django.core import signing
from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import escape
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import OutreachMessage, Suppression

SALT = 'outreach-unsubscribe'

PAGE = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex">
<title>Unsubscribe | Zubair Hussain</title></head>
<body style="margin:0;padding:56px 16px;background:#0a0a0a;background-image:radial-gradient(120% 90% at 100% 100%, rgba(200,20,30,0.45) 0%, rgba(200,20,30,0.12) 40%, rgba(10,10,10,0) 70%);min-height:100vh;box-sizing:border-box;font-family:'Segoe UI',Helvetica,Arial,sans-serif;color:#F5F4F0;">
<div style="max-width:440px;margin:0 auto;background:#121212;border:1px solid #2a1214;border-left:3px solid #C8141E;border-radius:16px;padding:30px 26px;">
<div style="font-family:Georgia,'Times New Roman',serif;font-style:italic;font-size:36px;line-height:1;">ZH<span style="color:#C8141E;">.</span></div>
<div style="margin-top:6px;font-size:12px;letter-spacing:1.4px;text-transform:uppercase;color:#a39f9a;">Zubair Hussain</div>
{content}
</div></body></html>"""

BUTTON = ('<p style="margin:22px 0 6px;font-size:16px;line-height:1.5;">Stop all emails to <b>{email}</b>?</p>'
          '<p style="margin:0 0 20px;font-size:14px;line-height:1.5;color:#a39f9a;">One click and you will not hear '
          'from me again.</p><form method="post"><button type="submit" style="background:#C8141E;'
          'background-image:linear-gradient(135deg,#E0202B 0%,#C8141E 55%,#7A0A10 100%);color:#fff;border:0;'
          'border-radius:10px;padding:13px 22px;font-size:15px;font-weight:600;cursor:pointer;">'
          'Unsubscribe</button></form>')
# The label that appears after the click (the page has no JavaScript: the app's security policy forbids it).
DONE_LABEL = ('<div role="status" style="margin-top:22px;padding:14px 16px;border-radius:10px;'
              'background:rgba(34,160,90,0.12);border:1px solid rgba(34,160,90,0.55);font-size:15px;line-height:1.5;">'
              '<b style="color:#4ade80;">&#10003; You are unsubscribed.</b><br>'
              '<span style="color:#F5F4F0;"><b>{email}</b> will not receive any more emails from me. '
              'Nothing else is needed.</span></div>')


def make_token(message):
    return signing.dumps({'id': message.pk}, salt=SALT)


def url_for(message):
    """Public https link, or '' when the backend has no public address (then mailto only)."""
    base = settings.OUTREACH_REVIEW_BASE_URL
    if not base.startswith('https://'):
        return ''
    return f"{base}{reverse('outreach-unsubscribe', args=[make_token(message)])}"


def unsubscribe_message(message):
    email = message.to_email.strip().lower()
    Suppression.objects.get_or_create(owner=message.owner, email=email,
                                      defaults={'reason': Suppression.Reason.OPT_OUT, 'note': 'One-click unsubscribe'})
    OutreachMessage.objects.filter(
        owner=message.owner, to_email__iexact=email,
        status__in=(OutreachMessage.Status.DRAFT, OutreachMessage.Status.QUEUED),
    ).update(status=OutreachMessage.Status.CANCELLED, skip_reason='Unsubscribed')
    return email


def _page(content, status=200):
    return HttpResponse(PAGE.format(content=content), status=status)


# The signed token is the credential, and mail apps POST without cookies (RFC 8058).
@csrf_exempt
@require_http_methods(['GET', 'POST'])
def unsubscribe_view(request, token):
    try:
        message_id = signing.loads(token, salt=SALT)['id']
    except (signing.BadSignature, KeyError, TypeError):
        return _page('<p style="margin-top:22px;">This link is not valid. Reply "unsubscribe" to the email instead.</p>',
                     status=400)
    message = OutreachMessage.objects.filter(pk=message_id).first()
    if message is None:
        return _page('<p style="margin-top:22px;">You will not hear from me again.</p>')
    email = message.to_email.strip().lower()
    if request.method == 'POST':
        unsubscribe_message(message)
        return _page(DONE_LABEL.format(email=escape(email)))
    if Suppression.objects.filter(owner=message.owner, email=email).exists():
        return _page(DONE_LABEL.format(email=escape(email)))
    return _page(BUTTON.format(email=escape(email)))
