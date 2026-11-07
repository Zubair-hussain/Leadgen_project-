"""Watch the sending mailbox over IMAP for replies, bounces and unsubscribes.

Runs every few minutes from Celery Beat, and always right before follow-ups are
scheduled. It only looks: the mailbox is opened read-only, nothing is marked read,
moved or deleted.

- A reply (In-Reply-To/References matches one of our Message-IDs, or it comes from an
  address we emailed) marks the thread replied and cancels its pending follow-ups.
  Out-of-office and other automatic replies do not count.
- A reply asking to unsubscribe, stop, or saying "not interested" also suppresses the address.
- A bounce (mailer-daemon, postmaster, delivery status notification) suppresses the address.
"""
import email
import imaplib
import logging
import re
import ssl
from datetime import timedelta
from email import policy
from email.utils import parseaddr

from django.conf import settings
from django.utils import timezone

from .models import OutreachMessage, Suppression

logger = logging.getLogger(__name__)

Status = OutreachMessage.Status
HEADER_FIELDS = 'FROM SUBJECT IN-REPLY-TO REFERENCES AUTO-SUBMITTED X-AUTOREPLY'
LIST_RE = re.compile(r'\((?P<flags>[^)]*)\)\s+(?:"[^"]*"|NIL)\s+(?P<name>.+)$')
MSGID_RE = re.compile(r'<[^<>\s]+>')
BOUNCE_FROM_RE = re.compile(r'^(mailer-daemon|postmaster|mail-daemon|bounce[s]?)@', re.IGNORECASE)
BOUNCE_SUBJECT_RE = re.compile(
    r'undeliver|delivery status notification|delivery has failed|mail delivery failed|returned mail|'
    r'failure notice|could not be delivered|delivery failure', re.IGNORECASE)
AUTO_REPLY_SUBJECT_RE = re.compile(r'out of (the )?office|automatic reply|auto[- ]?reply|autoreply|on vacation|away from',
                                   re.IGNORECASE)
OPT_OUT_RE = re.compile(
    r"\b(unsubscribe|remove me|take me off|stop (emailing|contacting|sending)|do ?n[o']t (email|contact)|"
    r"not interested|no thanks|no thank you)\b", re.IGNORECASE)
RECIPIENT_RE = re.compile(r'(?:final|original)-recipient:\s*rfc822;\s*<?([^\s<>;]+@[^\s<>;]+)>?', re.IGNORECASE)


class InboxError(Exception):
    """The mailbox could not be opened."""


def is_configured():
    return all([settings.OUTREACH_IMAP_HOST, settings.OUTREACH_IMAP_USER, settings.OUTREACH_IMAP_PASSWORD])


def connect():
    if not is_configured():
        raise InboxError('IMAP is not configured.')
    try:
        imap = imaplib.IMAP4_SSL(settings.OUTREACH_IMAP_HOST, settings.OUTREACH_IMAP_PORT,
                                 ssl_context=ssl.create_default_context(), timeout=30)
        imap.login(settings.OUTREACH_IMAP_USER, settings.OUTREACH_IMAP_PASSWORD)
    except imaplib.IMAP4.error as exc:
        raise InboxError(f'IMAP login failed for {settings.OUTREACH_IMAP_USER}: {exc}') from exc
    return imap


def _quote(name):
    name = name.strip()
    if name.startswith('"'):
        return name
    return f'"{name}"' if ' ' in name else name


def sent_folder(imap):
    """The folder flagged \\Sent, or OUTREACH_IMAP_SENT_FOLDER."""
    typ, rows = imap.list()
    if typ == 'OK':
        for row in rows or []:
            line = row.decode('utf-8', 'replace') if isinstance(row, bytes) else str(row)
            match = LIST_RE.match(line)
            if match and '\\sent' in match.group('flags').lower():
                return _quote(match.group('name'))
    return _quote(settings.OUTREACH_IMAP_SENT_FOLDER)


def _ids(value):
    return {m.lower() for m in MSGID_RE.findall(value or '')}


def _plain_text(msg):
    """The new text of a reply (quoted history removed), lower-cased, at most 3000 chars."""
    part = msg.get_body(preferencelist=('plain', 'html')) if msg.is_multipart() else msg
    try:
        text = part.get_content() if part is not None else ''
    except (KeyError, LookupError):
        text = ''
    text = re.sub(r'<[^>]+>', ' ', text)
    new = []
    for line in text.splitlines():
        if line.startswith('>') or re.match(r'^\s*on .+ wrote:\s*$', line, re.IGNORECASE):
            break
        new.append(line)
    return '\n'.join(new)[:3000].lower()


def _fetch(imap, uid, what):
    typ, data = imap.uid('fetch', uid, f'({what})')
    if typ != 'OK':
        return None
    for item in data or []:
        if isinstance(item, tuple) and len(item) > 1:
            return email.message_from_bytes(item[1], policy=policy.default)
    return None


def _suppress(owner, address, reason, note):
    address = (address or '').strip().lower()
    if not address:
        return False
    _, created = Suppression.objects.get_or_create(owner=owner, email=address,
                                                   defaults={'reason': reason, 'note': note[:255]})
    OutreachMessage.objects.filter(
        owner=owner, to_email__iexact=address, status__in=[Status.DRAFT, Status.QUEUED],
    ).update(status=Status.CANCELLED, skip_reason=note[:255])
    return created


def mark_replied(root, now):
    if root.replied_at is None:
        root.replied_at = now
        root.save(update_fields=['replied_at', 'updated_at'])
    return OutreachMessage.objects.filter(parent=root, status__in=[Status.DRAFT, Status.QUEUED]).update(
        status=Status.CANCELLED, skip_reason='Lead replied, so the follow-up was cancelled.')


def sync(now=None):
    """Scan recent INBOX mail. Returns counts of what was found."""
    now = now or timezone.now()
    result = {'replies': 0, 'bounces': 0, 'opt_outs': 0, 'scanned': 0}
    if not settings.OUTREACH_INBOX_SYNC_ENABLED or not is_configured():
        result['status'] = 'not-configured'
        return result

    lookback = now - timedelta(days=settings.OUTREACH_INBOX_LOOKBACK_DAYS)
    window = now - timedelta(days=settings.OUTREACH_INBOX_LOOKBACK_DAYS + sum(_followup_days()) + 7)
    sent = list(OutreachMessage.objects.filter(status=Status.SENT, sent_at__gte=window).select_related('parent'))
    by_id = {m.rfc_message_id.lower(): m for m in sent if m.rfc_message_id}
    by_address = {}
    for message in sorted(sent, key=lambda m: m.sent_at):
        by_address[message.to_email.lower()] = message
    own = (settings.OUTREACH_FROM_EMAIL or '').lower()
    if not sent:
        result['status'] = 'nothing-sent'
        return result

    try:
        imap = connect()
    except (InboxError, OSError) as exc:
        logger.warning("Inbox sync skipped: %s", exc)
        result['status'] = f'error: {exc}'[:200]
        return result
    try:
        imap.select('INBOX', readonly=True)
        typ, data = imap.uid('search', None, 'SINCE', lookback.strftime('%d-%b-%Y'))
        uids = (data[0].split() if typ == 'OK' and data and data[0] else [])[-settings.OUTREACH_INBOX_MAX_SCAN:]
        for uid in uids:
            headers = _fetch(imap, uid, f'BODY.PEEK[HEADER.FIELDS ({HEADER_FIELDS})]')
            if headers is None:
                continue
            result['scanned'] += 1
            sender = parseaddr(str(headers.get('From', '')))[1].lower()
            subject = str(headers.get('Subject', ''))
            if not sender or sender == own:
                continue

            if BOUNCE_FROM_RE.match(sender) or BOUNCE_SUBJECT_RE.search(subject):
                full = _fetch(imap, uid, 'BODY.PEEK[]')
                raw = full.as_string() if full is not None else ''
                target = next((by_id[i] for i in _ids(raw) if i in by_id), None)
                if target is None:
                    found = RECIPIENT_RE.search(raw)
                    target = by_address.get(found.group(1).lower()) if found else None
                if target is not None:
                    root = target.root
                    if root.bounced_at is None:
                        root.bounced_at = now
                        root.save(update_fields=['bounced_at', 'updated_at'])
                    if _suppress(target.owner, target.to_email, Suppression.Reason.BOUNCE,
                                 'Bounced: the address does not accept mail.'):
                        result['bounces'] += 1
                continue

            refs = _ids(str(headers.get('In-Reply-To', ''))) | _ids(str(headers.get('References', '')))
            target = next((by_id[i] for i in refs if i in by_id), None) or by_address.get(sender)
            if target is None:
                continue
            auto = str(headers.get('Auto-Submitted', 'no')).lower()
            if (auto and auto != 'no') or headers.get('X-Autoreply') or AUTO_REPLY_SUBJECT_RE.search(subject):
                continue

            root = target.root
            if root.replied_at is None:
                result['replies'] += 1
            mark_replied(root, now)
            full = _fetch(imap, uid, 'BODY.PEEK[]')
            text = f"{subject.lower()}\n{_plain_text(full) if full is not None else ''}"
            if OPT_OUT_RE.search(text) and _suppress(
                    root.owner, root.to_email, Suppression.Reason.OPT_OUT, 'Asked not to be contacted (reply).'):
                result['opt_outs'] += 1
    except (imaplib.IMAP4.error, OSError) as exc:
        logger.warning("Inbox sync stopped early: %s", exc)
        result['status'] = f'error: {exc}'[:200]
        return result
    finally:
        try:
            imap.logout()
        except (imaplib.IMAP4.error, OSError):
            pass
    result['status'] = 'ok'
    return result


def _followup_days():
    from .playbook import followup_days

    return followup_days()
