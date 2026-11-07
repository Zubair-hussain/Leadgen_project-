import smtplib
from datetime import datetime, timedelta
from email import message_from_bytes, policy
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from leads.models import Lead
from outreach import branding, followups, inbox, mailer, mime, playbook, smtp_client
from outreach.models import LeadResearch, OutreachMessage, Suppression
from outreach.services import preflight, process_queue, queue_status, thread_headers

WORK_TIME = timezone.make_aware(datetime(2026, 10, 13, 10, 0))  # Tuesday 10:00
GOOD_SUBJECT = 'bright smile online'
GOOD_BODY = ("Hi Bright Smile Dental team,\n\nYour 4.8 stars in Leeds say patients love you, but Google shows no "
             "website yet. I build fast, simple sites for local clinics. A one page site with your hours and a "
             "booking button would help new patients find you.\n\nWould you like a quick mock up?\n\nRegards,\nZubair")
SMTP = {
    'OUTREACH_TRANSPORT': 'smtp', 'OUTREACH_FROM_EMAIL': 'zubair@zubairhussain.xyz',
    'OUTREACH_FROM_NAME': 'Zubair Hussain', 'OUTREACH_SMTP_HOST': 'smtp.hostinger.com', 'OUTREACH_SMTP_PORT': 465,
    'OUTREACH_SMTP_SSL': True, 'OUTREACH_SMTP_USER': 'zubair@zubairhussain.xyz', 'OUTREACH_SMTP_PASSWORD': 'pw',
    'OUTREACH_IMAP_HOST': 'imap.hostinger.com', 'OUTREACH_IMAP_USER': 'zubair@zubairhussain.xyz',
    'OUTREACH_IMAP_PASSWORD': 'pw', 'OUTREACH_PORTFOLIO_URL': 'https://zubairhussain.xyz',
    'OUTREACH_NOTIFY_EMAIL': 'zubair@zubairhussain.xyz',
}


def make_user(name='owner'):
    return get_user_model().objects.create_user(username=name, password='pw')


def make_lead(owner, email='hello@brightsmile.co.uk', website=False, rating=4.8, reviews=120):
    lead = Lead.objects.create(owner=owner, email=email, source='google-maps', category='Dentists',
                               location='Leeds', is_verified=True)
    LeadResearch.objects.create(lead=lead, status='ok', data={
        'name': 'Bright Smile Dental', 'rating': rating, 'reviews': reviews, 'has_website': website})
    return lead


def sent_root(owner, email='hello@brightsmile.co.uk', sent_at=WORK_TIME, **kwargs):
    lead = make_lead(owner, email=email)
    return OutreachMessage.objects.create(
        owner=owner, lead=lead, to_email=email, subject=GOOD_SUBJECT, body=GOOD_BODY, status='sent',
        sent_at=sent_at, approved_at=sent_at, rfc_message_id=f'<first.{email}@zubairhussain.xyz>', **kwargs)


class PlaybookTests(TestCase):
    def test_good_email_scores_high(self):
        graded = playbook.score(GOOD_SUBJECT, GOOD_BODY, {'name': 'Bright Smile Dental', 'location': 'Leeds'})
        self.assertGreaterEqual(graded['score'], 90, graded['notes'])

    def test_bad_email_gets_specific_notes(self):
        body = ("Hi,\n\nI am a web developer. " + "I build websites for many clients. " * 12
                + "\n\nRegards,\nZubair")
        graded = playbook.score('Amazing Website Design Services For Your Local Business Today', body,
                                {'name': 'Bright Smile Dental'})
        self.assertLess(graded['score'], 50)
        notes = ' '.join(graded['notes'])
        for expected in ('No clear ask', 'Opens with you', 'Nothing in it is about', 'Subject is long', 'Title Case'):
            self.assertIn(expected, notes)

    def test_hooks_use_town_not_street(self):
        self.assertEqual(playbook.personal_hooks({'category': 'Dentists', 'location': '2-4 Exchange St, Manchester'}),
                         ['dentist', 'manchester'])

    @override_settings(OUTREACH_WARMUP_ENABLED=True, OUTREACH_WARMUP_START=5, OUTREACH_WARMUP_STEP=2,
                       OUTREACH_DAILY_LIMIT=30, OUTREACH_DAILY_MIN=30)
    def test_warmup_ramps_to_cap(self):
        self.assertEqual(playbook.daily_limit(WORK_TIME), 5)
        sent_root(make_user(), sent_at=WORK_TIME)
        self.assertEqual(playbook.daily_limit(WORK_TIME + timedelta(days=4)), 13)
        self.assertEqual(playbook.daily_limit(WORK_TIME + timedelta(days=60)), 30)
        with override_settings(OUTREACH_WARMUP_ENABLED=False):
            self.assertEqual(playbook.daily_limit(WORK_TIME), 30)

    def test_priority_prefers_followups_then_no_website(self):
        user = make_user()
        no_site = OutreachMessage(owner=user, lead=make_lead(user, 'a@a.co.uk'), to_email='a@a.co.uk',
                                  subject=GOOD_SUBJECT, body=GOOD_BODY)
        has_site = OutreachMessage(owner=user, lead=make_lead(user, 'b@b.co.uk', website=True), to_email='b@b.co.uk',
                                   subject=GOOD_SUBJECT, body=GOOD_BODY)
        followup = OutreachMessage(owner=user, to_email='c@gmail.com', subject='Re: x', body='Hi', sequence_step=1)
        self.assertGreater(playbook.priority(followup), playbook.priority(no_site))
        self.assertGreater(playbook.priority(no_site), playbook.priority(has_site))

    @override_settings(OUTREACH_FOLLOWUP_DAYS='3, 4,x,7', OUTREACH_PORTFOLIO_URL='https://zubairhussain.xyz')
    def test_followup_texts_are_clean_and_end_with_breakup(self):
        from outreach import humanizer

        root = sent_root(make_user())
        self.assertEqual(playbook.followup_days(), [3, 4, 7])
        for step in (1, 2, 3):
            subject, body = playbook.followup_text(root, step)
            self.assertEqual(subject, f'Re: {GOOD_SUBJECT}')
            self.assertTrue(body.startswith('Hi Bright Smile Dental team,'))
            self.assertEqual(humanizer.check(subject, body), [], body)
        self.assertIn('zubairhussain.xyz', body)
        self.assertIn("I'll leave it here", body)


@override_settings(**SMTP)
class BrandingTests(TestCase):
    def test_text_has_signature_then_opt_out(self):
        text, html = branding.compose(GOOD_SUBJECT, GOOD_BODY)
        self.assertIn('--\nZubair Hussain\nFull Stack Developer | zubairhussain.xyz', text)
        self.assertIn("I won't contact you again.", text)
        self.assertIn('Sent by Zubair Hussain', text)
        self.assertIn('ZH<span style="color:#C8141E;">.</span>', html)
        self.assertIn('Would you like a quick mock up?', html)

    def test_html_escapes_and_links(self):
        html = branding.html_version('s', 'Hi <b>team</b>,\n\nSee https://zubairhussain.xyz/work.')
        self.assertIn('&lt;b&gt;team&lt;/b&gt;', html)
        self.assertIn('<a href="https://zubairhussain.xyz/work"', html)

    @override_settings(OUTREACH_HTML_EMAIL=False, OUTREACH_SIGNATURE=False)
    def test_can_turn_off(self):
        text, html = branding.compose('s', 'Hello')
        self.assertIsNone(html)
        self.assertFalse(text.startswith('Hello\n\n--'))

    def test_preview_command_writes_file(self):
        with TemporaryDirectory() as folder:
            out = Path(folder) / 'p.html'
            stdout = StringIO()
            call_command('preview_outreach_email', out=str(out), stdout=stdout)
            self.assertIn('ZH', out.read_text(encoding='utf-8'))
            self.assertIn('Playbook score', stdout.getvalue())
            call_command('preview_outreach_email', '--signature-only', out=str(out), stdout=StringIO())
            page = out.read_text(encoding='utf-8')
            self.assertIn('Identities / Signatures', page)
            self.assertIn('radial-gradient', page)
            self.assertNotIn('unsubscribe', page)


@override_settings(**SMTP)
class SmtpTests(TestCase):
    def test_mime_threads_and_has_html(self):
        message = mime.build_mime('a@b.co', 'Re: s', 'text', html='<p>hi</p>', message_id='<m2@x>',
                                  in_reply_to='<m1@x>', references='<m0@x> <m1@x>')
        self.assertEqual((message['In-Reply-To'], message['References'], message['Message-ID']),
                         ('<m1@x>', '<m0@x> <m1@x>', '<m2@x>'))
        self.assertEqual(message['From'], 'Zubair Hussain <zubair@zubairhussain.xyz>')
        self.assertEqual([p.get_content_type() for p in message.iter_parts()], ['text/plain', 'text/html'])

    @patch('outreach.smtp_client.save_to_sent', return_value=True)
    @patch('outreach.smtp_client.smtplib.SMTP_SSL')
    def test_send_logs_in_and_returns_message_id(self, smtp_ssl, _saved):
        server = smtp_ssl.return_value
        server.send_message.return_value = {}
        message_id, thread = mailer.send_message('a@b.co', 'S', 'Body', html='<p>x</p>', message_id='<id@x>')
        self.assertEqual((message_id, thread), ('<id@x>', ''))
        smtp_ssl.assert_called_once()
        self.assertEqual(smtp_ssl.call_args.args, ('smtp.hostinger.com', 465))
        server.login.assert_called_once_with('zubair@zubairhussain.xyz', 'pw')
        server.quit.assert_called_once()

    @patch('outreach.smtp_client.smtplib.SMTP_SSL')
    def test_errors_are_wrapped(self, smtp_ssl):
        smtp_ssl.return_value.login.side_effect = smtplib.SMTPAuthenticationError(535, b'bad')
        with self.assertRaisesRegex(smtp_client.SmtpError, 'mailbox password'):
            smtp_client.send_message('a@b.co', 'S', 'B')
        smtp_ssl.return_value.login.side_effect = None
        smtp_ssl.return_value.send_message.side_effect = smtplib.SMTPRecipientsRefused({'a@b.co': (550, b'no')})
        with self.assertRaisesRegex(smtp_client.SmtpError, 'Recipient refused'):
            smtp_client.send_message('a@b.co', 'S', 'B')

    @override_settings(OUTREACH_SMTP_SSL=False, OUTREACH_SMTP_PORT=587)
    @patch('outreach.smtp_client.smtplib.SMTP')
    def test_starttls_mode(self, smtp):
        smtp_client.connect()
        smtp.return_value.starttls.assert_called_once()

    @patch('outreach.inbox.imaplib.IMAP4_SSL')
    def test_copy_saved_to_sent_folder(self, imap_cls):
        imap = imap_cls.return_value
        imap.__enter__.return_value = imap
        imap.list.return_value = ('OK', [b'(\\HasNoChildren) "." "INBOX"', b'(\\HasNoChildren \\Sent) "." "INBOX.Sent"'])
        self.assertTrue(smtp_client.save_to_sent(mime.build_mime('a@b.co', 'S', 'B')))
        self.assertEqual(imap.append.call_args.args[0], '"INBOX.Sent"')

    def test_not_configured_without_password(self):
        with override_settings(OUTREACH_SMTP_PASSWORD=''):
            self.assertFalse(mailer.is_configured())
            self.assertFalse(queue_status()['mail_configured'])
        self.assertEqual(queue_status()['transport'], 'smtp')

    @override_settings(OUTREACH_DRY_RUN=False)
    @patch('outreach.mailer.smtp_client.send_message', return_value=('<x@zubairhussain.xyz>', ''))
    def test_queue_sends_branded_email_over_smtp(self, send):
        user = make_user()
        lead = make_lead(user)
        message = OutreachMessage.objects.create(owner=user, lead=lead, to_email=lead.email, subject=GOOD_SUBJECT,
                                                 body=GOOD_BODY, status='queued', approved_at=WORK_TIME)
        with patch('outreach.services.research.send_blocker', return_value=''):
            self.assertEqual(process_queue(WORK_TIME), 'sent')
        message.refresh_from_db()
        self.assertTrue(message.rfc_message_id.endswith('@zubairhussain.xyz>'))
        self.assertEqual(send.call_args.kwargs['message_id'], message.rfc_message_id)
        self.assertIn('ZH', send.call_args.kwargs['html'])
        with override_settings(OUTREACH_SMTP_PASSWORD=''):
            self.assertEqual(process_queue(WORK_TIME), 'smtp-not-configured')

    @patch('outreach.management.commands.check_mailbox.inbox.connect')
    @patch('outreach.management.commands.check_mailbox.smtp_client.connect')
    @patch('outreach.mailer.smtp_client.send_message', return_value=('<t@x>', ''))
    def test_check_mailbox_command(self, send, smtp_connect, imap_connect):
        imap = imap_connect.return_value.__enter__.return_value
        imap.list.return_value = ('OK', [b'(\\Sent) "." Sent'])
        out = StringIO()
        call_command('check_mailbox', '--send-test', stdout=out)
        self.assertIn('SMTP login OK', out.getvalue())
        self.assertIn('Sent folder: Sent', out.getvalue())
        self.assertEqual(send.call_args.args[0], 'zubair@zubairhussain.xyz')


@override_settings(**SMTP, OUTREACH_FOLLOWUP_DAYS='3,4,7', OUTREACH_INBOX_SYNC_ENABLED=False)
class FollowupTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.root = sent_root(self.user)

    def test_waits_then_queues_first_followup(self):
        self.assertEqual(followups.schedule_followups(WORK_TIME + timedelta(days=2))['queued'], 0)
        self.assertEqual(followups.schedule_followups(WORK_TIME + timedelta(days=3))['queued'], 1)
        followup = OutreachMessage.objects.get(parent=self.root)
        self.assertEqual((followup.status, followup.sequence_step, followup.subject),
                         ('queued', 1, f'Re: {GOOD_SUBJECT}'))
        self.assertGreaterEqual(followup.priority, 100)
        # Re: is honest here and the earlier email in the thread is not a "re-contact".
        self.assertEqual(preflight(followup), [])
        # Only one at a time: nothing new while step 1 is still queued.
        self.assertEqual(followups.schedule_followups(WORK_TIME + timedelta(days=30))['queued'], 0)

    def test_full_sequence_then_stops(self):
        when = WORK_TIME
        for step, wait in enumerate([3, 4, 7], 1):
            when += timedelta(days=wait)
            self.assertEqual(followups.schedule_followups(when)['queued'], 1, step)
            OutreachMessage.objects.filter(parent=self.root, sequence_step=step).update(
                status='sent', sent_at=when, rfc_message_id=f'<f{step}@zubairhussain.xyz>')
        self.assertEqual(followups.schedule_followups(when + timedelta(days=30))['queued'], 0)
        last = OutreachMessage.objects.get(parent=self.root, sequence_step=3)
        headers = thread_headers(last)
        self.assertEqual(headers['in_reply_to'], '<f2@zubairhussain.xyz>')
        self.assertEqual(headers['references'].split()[0], self.root.rfc_message_id)

    def test_no_followup_after_reply_bounce_or_opt_out(self):
        later = WORK_TIME + timedelta(days=5)
        OutreachMessage.objects.filter(pk=self.root.pk).update(replied_at=WORK_TIME)
        self.assertEqual(followups.schedule_followups(later)['queued'], 0)
        OutreachMessage.objects.filter(pk=self.root.pk).update(replied_at=None, bounced_at=WORK_TIME)
        self.assertEqual(followups.schedule_followups(later)['queued'], 0)
        OutreachMessage.objects.filter(pk=self.root.pk).update(bounced_at=None)
        Suppression.objects.create(owner=self.user, email=self.root.to_email)
        self.assertEqual(followups.schedule_followups(later)['queued'], 0)

    def test_queued_followup_blocked_if_reply_arrives(self):
        followups.schedule_followups(WORK_TIME + timedelta(days=3))
        followup = OutreachMessage.objects.get(parent=self.root)
        OutreachMessage.objects.filter(pk=self.root.pk).update(replied_at=WORK_TIME)
        followup.refresh_from_db()
        self.assertIn("Lead already replied, so no follow-up.", preflight(followup))

    @override_settings(OUTREACH_FOLLOWUPS_ENABLED=False)
    def test_can_be_disabled(self):
        self.assertEqual(followups.schedule_followups(WORK_TIME + timedelta(days=9))['queued'], 0)


def raw_email(sender, subject, body='Thanks', in_reply_to='', extra=''):
    headers = f"From: {sender}\r\nTo: zubair@zubairhussain.xyz\r\nSubject: {subject}\r\n"
    if in_reply_to:
        headers += f"In-Reply-To: {in_reply_to}\r\nReferences: {in_reply_to}\r\n"
    return (headers + extra + "Content-Type: text/plain; charset=utf-8\r\n\r\n" + body).encode()


class FakeImap:
    def __init__(self, messages):
        self.messages = messages
        self.readonly = None

    def login(self, user, password):
        return 'OK', [b'']

    def select(self, folder, readonly=False):
        self.readonly = readonly
        return 'OK', [str(len(self.messages)).encode()]

    def uid(self, command, *args):
        if command == 'search':
            return 'OK', [' '.join(str(i + 1) for i in range(len(self.messages))).encode()]
        raw = self.messages[int(args[0]) - 1]
        return 'OK', [(b'1 (BODY[] {%d}' % len(raw), raw), b')']

    def logout(self):
        return 'BYE', []


@override_settings(**SMTP)
class InboxTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.root = sent_root(self.user, sent_at=timezone.now() - timedelta(days=1))
        self.followup = OutreachMessage.objects.create(
            owner=self.user, lead=self.root.lead, parent=self.root, sequence_step=1, to_email=self.root.to_email,
            subject='Re: x', body='Hi', status='queued', approved_at=timezone.now())

    def sync(self, *messages):
        fake = FakeImap(list(messages))
        with patch('outreach.inbox.imaplib.IMAP4_SSL', return_value=fake):
            result = inbox.sync()
        self.assertTrue(fake.readonly)  # never marks anything read
        return result

    def test_reply_stops_sequence(self):
        result = self.sync(raw_email('Dr Smile <dr@other.co.uk>', 'Re: bright smile online',
                                     in_reply_to=self.root.rfc_message_id))
        self.assertEqual(result['replies'], 1)
        self.root.refresh_from_db()
        self.followup.refresh_from_db()
        self.assertIsNotNone(self.root.replied_at)
        self.assertEqual(self.followup.status, 'cancelled')
        self.assertFalse(Suppression.objects.exists())

    def test_out_of_office_is_ignored(self):
        self.sync(raw_email(self.root.to_email, 'Automatic reply: away', in_reply_to=self.root.rfc_message_id),
                  raw_email(self.root.to_email, 'Hello', extra='Auto-Submitted: auto-replied\r\n'))
        self.root.refresh_from_db()
        self.assertIsNone(self.root.replied_at)

    def test_unsubscribe_reply_suppresses(self):
        result = self.sync(raw_email(self.root.to_email, 'unsubscribe', body='Please remove me.\n> old quote'))
        self.assertEqual((result['replies'], result['opt_outs']), (1, 1))
        self.assertEqual(Suppression.objects.get().reason, 'opt_out')

    def test_quoted_text_does_not_count_as_opt_out(self):
        self.sync(raw_email(self.root.to_email, 'Re: hi', body="Sounds good, call me.\n> reply unsubscribe to stop"))
        self.assertFalse(Suppression.objects.exists())

    def test_bounce_suppresses(self):
        dsn = (f"Final-Recipient: rfc822; {self.root.to_email}\r\nAction: failed\r\n"
               f"Original-Message-ID: {self.root.rfc_message_id}")
        result = self.sync(raw_email('MAILER-DAEMON@mx.hostinger.com', 'Undelivered Mail Returned to Sender', body=dsn))
        self.assertEqual(result['bounces'], 1)
        self.root.refresh_from_db()
        self.assertIsNotNone(self.root.bounced_at)
        self.assertEqual(Suppression.objects.get().reason, 'bounce')

    def test_skips_cleanly_when_not_configured_or_down(self):
        with override_settings(OUTREACH_IMAP_PASSWORD=''):
            self.assertEqual(inbox.sync()['status'], 'not-configured')
        with patch('outreach.inbox.imaplib.IMAP4_SSL', side_effect=OSError('offline')):
            self.assertTrue(inbox.sync()['status'].startswith('error'))

    def test_sent_folder_fallback(self):
        imap = MagicMock()
        imap.list.return_value = ('OK', [b'(\\HasNoChildren) "." "INBOX"'])
        self.assertEqual(inbox.sent_folder(imap), 'INBOX.Sent')
        parsed = message_from_bytes(raw_email('a@b.co', 's', body='new\n> old'), policy=policy.default)
        self.assertEqual(inbox._plain_text(parsed).strip(), 'new')
