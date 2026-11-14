"""Build the MIME message every transport sends."""
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid

from django.conf import settings


def new_message_id():
    domain = (settings.OUTREACH_FROM_EMAIL or 'localhost').split('@')[-1]
    return make_msgid(domain=domain)


def reply_to_address():
    """Where replies and mailto opt-outs go: OUTREACH_REPLY_TO, else the From address."""
    return settings.OUTREACH_REPLY_TO.strip() or settings.OUTREACH_FROM_EMAIL


def list_unsubscribe_header(unsubscribe_url=''):
    """RFC 2369/8058: the https one-click link first (Gmail/Outlook button), mailto as a fallback."""
    mailto = f'<mailto:{reply_to_address()}?subject=unsubscribe>'
    return f'<{unsubscribe_url}>, {mailto}' if unsubscribe_url else mailto


def build_mime(to_email, subject, body, list_unsubscribe=True, html=None, message_id=None,
               in_reply_to='', references='', unsubscribe_url=''):
    """Plain text always; an HTML alternative when given. in_reply_to/references thread a follow-up."""
    from_email = settings.OUTREACH_FROM_EMAIL
    message = EmailMessage()
    message['To'] = to_email
    message['From'] = formataddr((settings.OUTREACH_FROM_NAME, from_email)) if settings.OUTREACH_FROM_NAME else from_email
    message['Subject'] = subject
    message['Date'] = formatdate(localtime=True)
    message['Message-ID'] = message_id or new_message_id()
    reply_to = reply_to_address()
    if reply_to.lower() != (from_email or '').lower():
        message['Reply-To'] = reply_to
    if in_reply_to:
        message['In-Reply-To'] = in_reply_to
        message['References'] = references or in_reply_to
    if list_unsubscribe:
        message['List-Unsubscribe'] = list_unsubscribe_header(unsubscribe_url)
        if unsubscribe_url:
            message['List-Unsubscribe-Post'] = 'List-Unsubscribe=One-Click'
    message.set_content(body)
    if html:
        message.add_alternative(html, subtype='html')
    return message
