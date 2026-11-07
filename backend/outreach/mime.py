"""Build the MIME message every transport sends."""
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid

from django.conf import settings


def new_message_id():
    domain = (settings.OUTREACH_FROM_EMAIL or 'localhost').split('@')[-1]
    return make_msgid(domain=domain)


def build_mime(to_email, subject, body, list_unsubscribe=True, html=None, message_id=None,
               in_reply_to='', references=''):
    """Plain text always; an HTML alternative when given. in_reply_to/references thread a follow-up."""
    from_email = settings.OUTREACH_FROM_EMAIL
    message = EmailMessage()
    message['To'] = to_email
    message['From'] = formataddr((settings.OUTREACH_FROM_NAME, from_email)) if settings.OUTREACH_FROM_NAME else from_email
    message['Subject'] = subject
    message['Date'] = formatdate(localtime=True)
    message['Message-ID'] = message_id or new_message_id()
    if in_reply_to:
        message['In-Reply-To'] = in_reply_to
        message['References'] = references or in_reply_to
    if list_unsubscribe:
        message['List-Unsubscribe'] = f'<mailto:{from_email}?subject=unsubscribe>'
    message.set_content(body)
    if html:
        message.add_alternative(html, subtype='html')
    return message
