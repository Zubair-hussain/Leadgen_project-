from datetime import datetime, timedelta
from io import StringIO
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from leads.models import Lead
from outreach import gmail
from outreach.models import OutreachMessage, SendThrottle, Suppression
from outreach.services import final_body, in_send_window, preflight, process_queue

# Tuesday 10:00 in the project's TIME_ZONE: inside the default send window.
WORK_TIME = timezone.make_aware(datetime(2026, 10, 13, 10, 0))

GMAIL_SETTINGS = {
    'GOOGLE_CLIENT_ID': 'cid',
    'GOOGLE_CLIENT_SECRET': 'secret',
    'GOOGLE_REFRESH_TOKEN': 'refresh',
    'OUTREACH_FROM_EMAIL': 'me@mydomain.com',
    'OUTREACH_FROM_NAME': 'Zubair',
}


def make_user(name='owner'):
    return get_user_model().objects.create_user(username=name, password='pw')


def make_message(owner, email='james@dental.co.uk', status=OutreachMessage.Status.QUEUED, **kwargs):
    lead = Lead.objects.create(owner=owner, email=email, source='google-maps', is_verified=True)
    defaults = {
        'subject': 'A website concept for ABC Dental',
        'body': 'Hi James,\n\nI put together a small concept for your clinic.\n\nRegards,\nZubair',
        'approved_at': WORK_TIME - timedelta(minutes=5),
    }
    defaults.update(kwargs)
    return OutreachMessage.objects.create(owner=owner, lead=lead, to_email=email, status=status, **defaults)


class PreflightTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_clean_message_passes(self):
        self.assertEqual(preflight(make_message(self.user, status='draft')), [])

    def test_suppressed_recipient_blocked(self):
        message = make_message(self.user, status='draft')
        Suppression.objects.create(owner=self.user, email='JAMES@dental.co.uk')
        self.assertIn("Recipient is on the suppression list.", preflight(message))

    def test_unverified_lead_blocked(self):
        message = make_message(self.user, status='draft')
        message.lead.is_verified = False
        message.lead.save()
        self.assertIn("Lead email is not verified yet (run Verify first).", preflight(message))

    def test_manual_address_needs_mx(self):
        message = OutreachMessage.objects.create(
            owner=self.user, to_email='x@nomx.co.uk', subject='Hello', body='Hi there')
        with patch('outreach.services.EmailVerifier.verify_domain', return_value=False):
            self.assertIn("Recipient domain has no MX records.", preflight(message))

    def test_invalid_syntax_blocked(self):
        message = OutreachMessage.objects.create(
            owner=self.user, to_email='noreply@shop.com', subject='Hello', body='Hi')
        self.assertIn("Invalid email address.", preflight(message))

    def test_recent_real_contact_blocked_but_dry_run_ignored(self):
        make_message(self.user, status='sent', sent_at=timezone.now() - timedelta(days=2), dry_run=True)
        message = OutreachMessage.objects.create(
            owner=self.user, lead=Lead.objects.get(), to_email='james@dental.co.uk', subject='Hi', body='Hi')
        self.assertEqual(preflight(message), [])

        OutreachMessage.objects.filter(status='sent').update(dry_run=False)
        self.assertIn("Already contacted in the last 30 days.", preflight(message))

    def test_duplicate_queued_blocked(self):
        make_message(self.user)
        message = OutreachMessage.objects.create(
            owner=self.user, lead=Lead.objects.get(), to_email='james@dental.co.uk', subject='Hi', body='Hi')
        self.assertIn("Another email to this address is already queued.", preflight(message))

    def test_content_rules(self):
        message = make_message(self.user, status='draft', subject='Re: your website',
                               body='a http://a.com b http://b.com c http://c.com')
        problems = preflight(message)
        self.assertIn("Subject must not start with Re:/Fwd: on a first email.", problems)
        self.assertIn("Body has more than 2 links.", problems)

    def test_opt_out_line_appended(self):
        self.assertTrue(final_body('Hello').endswith("I won't contact you again."))
        with override_settings(OUTREACH_OPT_OUT_LINE=''):
            self.assertEqual(final_body('Hello'), 'Hello')


class SendWindowTests(TestCase):
    def test_window(self):
        self.assertTrue(in_send_window(WORK_TIME))
        self.assertFalse(in_send_window(WORK_TIME.replace(hour=20)))
        self.assertFalse(in_send_window(WORK_TIME + timedelta(days=4)))  # Saturday
        with override_settings(OUTREACH_WEEKDAYS_ONLY=False):
            self.assertTrue(in_send_window(WORK_TIME + timedelta(days=4)))


@override_settings(**GMAIL_SETTINGS, OUTREACH_DRY_RUN=False)
class ProcessQueueTests(TestCase):
    def setUp(self):
        self.user = make_user()

    @patch('outreach.mailer.send_message', return_value=('gid', 'tid'))
    def test_sends_one_and_sets_delay(self, send):
        first = make_message(self.user)
        second = make_message(self.user, email='anna@clinic.co.uk')

        self.assertEqual(process_queue(WORK_TIME), 'sent')
        first.refresh_from_db()
        self.assertEqual((first.status, first.gmail_message_id, first.gmail_thread_id), ('sent', 'gid', 'tid'))
        self.assertIn("I won't contact you again.", send.call_args.args[2])

        throttle = SendThrottle.objects.get()
        self.assertGreaterEqual(throttle.next_send_at, WORK_TIME + timedelta(seconds=180))
        self.assertLessEqual(throttle.next_send_at, WORK_TIME + timedelta(seconds=480))

        self.assertEqual(process_queue(WORK_TIME + timedelta(seconds=60)), 'waiting-for-delay')
        self.assertEqual(process_queue(WORK_TIME + timedelta(minutes=9)), 'sent')
        second.refresh_from_db()
        self.assertEqual(second.status, 'sent')
        self.assertEqual(process_queue(WORK_TIME + timedelta(minutes=20)), 'queue-empty')

    def test_limits_and_window(self):
        make_message(self.user)
        self.assertEqual(process_queue(WORK_TIME.replace(hour=22)), 'outside-send-window')
        with override_settings(OUTREACH_DAILY_LIMIT=0):
            self.assertEqual(process_queue(WORK_TIME), 'daily-limit-reached')
        with override_settings(OUTREACH_HOURLY_LIMIT=0):
            self.assertEqual(process_queue(WORK_TIME), 'hourly-limit-reached')

    @override_settings(GOOGLE_REFRESH_TOKEN='')
    def test_refuses_without_gmail_config(self):
        make_message(self.user)
        self.assertEqual(process_queue(WORK_TIME), 'gmail-not-configured')

    def test_skips_if_suppressed_after_approval(self):
        message = make_message(self.user)
        Suppression.objects.create(owner=self.user, email=message.to_email, reason='opt_out')
        self.assertEqual(process_queue(WORK_TIME), 'skipped')
        message.refresh_from_db()
        self.assertEqual(message.status, 'skipped')
        self.assertEqual(message.skip_reason, "Recipient is on the suppression list.")

    @patch('outreach.mailer.send_message', side_effect=gmail.GmailError('boom'))
    def test_failure_recorded(self, _send):
        message = make_message(self.user)
        self.assertEqual(process_queue(WORK_TIME), 'failed')
        message.refresh_from_db()
        self.assertEqual((message.status, message.error), ('failed', 'boom'))

    @override_settings(OUTREACH_DRY_RUN=True, GOOGLE_REFRESH_TOKEN='')
    @patch('outreach.mailer.send_message')
    def test_dry_run_never_calls_gmail(self, send):
        message = make_message(self.user)
        self.assertEqual(process_queue(WORK_TIME), 'sent')
        message.refresh_from_db()
        self.assertTrue(message.dry_run)
        self.assertEqual(message.gmail_message_id, f'dry-run-{message.pk}')
        send.assert_not_called()


@override_settings(**GMAIL_SETTINGS)
class GmailClientTests(TestCase):
    @patch('outreach.gmail.requests.post')
    def test_send_message(self, post):
        post.side_effect = [
            Mock(status_code=200, json=lambda: {'access_token': 'tok'}),
            Mock(status_code=200, json=lambda: {'id': 'm1', 'threadId': 't1'}),
        ]
        self.assertEqual(gmail.send_message('a@b.co', 'Subj', 'Body'), ('m1', 't1'))
        send_call = post.call_args_list[1]
        self.assertEqual(send_call.kwargs['headers']['Authorization'], 'Bearer tok')
        self.assertIn('raw', send_call.kwargs['json'])

    def test_mime_headers(self):
        mime = gmail.build_mime('a@b.co', 'Subj', 'Body')
        self.assertEqual(mime['From'], 'Zubair <me@mydomain.com>')
        self.assertEqual(mime['List-Unsubscribe'], '<mailto:me@mydomain.com?subject=unsubscribe>')

    @patch('outreach.gmail.requests.post')
    def test_token_error(self, post):
        post.return_value = Mock(status_code=400, text='invalid_grant')
        with self.assertRaises(gmail.GmailError):
            gmail.get_access_token()

    @patch('outreach.gmail.requests.post')
    def test_send_error(self, post):
        post.side_effect = [
            Mock(status_code=200, json=lambda: {'access_token': 'tok'}),
            Mock(status_code=403, text='forbidden'),
        ]
        with self.assertRaises(gmail.GmailError):
            gmail.send_message('a@b.co', 'Subj', 'Body')


@override_settings(OUTREACH_DAILY_LIMIT=10, OUTREACH_HOURLY_LIMIT=5)
class OutreachApiTests(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.other = make_user('other')
        self.client.force_authenticate(self.user)
        self.lead = Lead.objects.create(owner=self.user, email='james@dental.co.uk',
                                        source='google-maps', is_verified=True)

    def create_draft(self, **data):
        payload = {'lead_id': self.lead.id, 'subject': 'A concept for ABC Dental', 'body': 'Hi James'}
        payload.update(data)
        return self.client.post('/api/outreach/messages/', payload, format='json')

    def test_requires_auth(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/outreach/messages/').status_code, 401)

    def test_draft_approve_cancel_flow(self):
        response = self.create_draft()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['to_email'], 'james@dental.co.uk')
        self.assertEqual(response.data['status'], 'draft')
        pk = response.data['id']

        self.assertTrue(self.client.get(f'/api/outreach/messages/{pk}/preflight/').data['ok'])
        approved = self.client.post(f'/api/outreach/messages/{pk}/approve/')
        self.assertEqual(approved.data['status'], 'queued')
        self.assertIsNotNone(approved.data['approved_at'])

        self.assertEqual(self.client.patch(f'/api/outreach/messages/{pk}/', {'body': 'x'}).status_code, 409)
        self.assertEqual(self.client.post(f'/api/outreach/messages/{pk}/approve/').status_code, 409)
        self.assertEqual(self.client.post(f'/api/outreach/messages/{pk}/cancel/').data['status'], 'cancelled')
        self.assertEqual(self.client.post(f'/api/outreach/messages/{pk}/cancel/').status_code, 409)

    def test_approve_blocked_by_checks(self):
        pk = self.create_draft(subject='Re: hello').data['id']
        response = self.client.post(f'/api/outreach/messages/{pk}/approve/')
        self.assertEqual(response.status_code, 400)
        self.assertIn("Subject must not start with Re:/Fwd: on a first email.", response.data['problems'])

    def test_cannot_use_other_users_lead_or_message(self):
        foreign = Lead.objects.create(owner=self.other, email='x@other.co.uk', source='x')
        self.assertEqual(self.create_draft(lead_id=foreign.id).status_code, 400)
        theirs = OutreachMessage.objects.create(owner=self.other, to_email='x@other.co.uk', subject='s', body='b')
        self.assertEqual(self.client.post(f'/api/outreach/messages/{theirs.pk}/approve/').status_code, 404)

    def test_needs_an_email(self):
        no_email = Lead.objects.create(owner=self.user, email=None, source='x')
        self.assertEqual(self.create_draft(lead_id=no_email.id).status_code, 400)

    def test_edit_and_delete_draft_and_word_warning(self):
        pk = self.create_draft().data['id']
        long_body = 'word ' * 200
        response = self.client.patch(f'/api/outreach/messages/{pk}/', {'body': long_body}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['warnings'], ["Body is 200 words; aim for 150 or fewer."])
        self.assertEqual(self.client.delete(f'/api/outreach/messages/{pk}/').status_code, 204)

    def test_sent_messages_cannot_be_deleted(self):
        message = OutreachMessage.objects.create(owner=self.user, to_email='a@b.co.uk', subject='s',
                                                 body='b', status='sent')
        self.assertEqual(self.client.delete(f'/api/outreach/messages/{message.pk}/').status_code, 409)

    def test_status_filter(self):
        self.create_draft()
        self.assertEqual(self.client.get('/api/outreach/messages/?status=draft').data['count'], 1)
        self.assertEqual(self.client.get('/api/outreach/messages/?status=sent').data['count'], 0)

    def test_suppression_cancels_pending_and_is_idempotent(self):
        pk = self.create_draft().data['id']
        first = self.client.post('/api/outreach/suppressions/',
                                 {'email': 'James@Dental.co.uk', 'reason': 'opt_out'}, format='json')
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.data['email'], 'james@dental.co.uk')
        self.assertEqual(OutreachMessage.objects.get(pk=pk).status, 'cancelled')

        again = self.client.post('/api/outreach/suppressions/', {'email': 'james@dental.co.uk'}, format='json')
        self.assertEqual(again.status_code, 200)
        self.assertEqual(self.client.get('/api/outreach/suppressions/').data['count'], 1)
        self.assertEqual(self.client.delete(f"/api/outreach/suppressions/{first.data['id']}/").status_code, 204)

    def test_status_endpoint(self):
        data = self.client.get('/api/outreach/status/').data
        self.assertTrue(data['dry_run'])
        self.assertEqual(data['daily_limit'], 10)
        self.assertIn('gmail_configured', data)


@override_settings(OUTREACH_DAILY_LIMIT=10, OUTREACH_HOURLY_LIMIT=5)
class CommandTests(TestCase):
    def test_process_command_prints_status(self):
        out = StringIO()
        with patch('outreach.management.commands.process_outreach_queue.process_queue', return_value='queue-empty'):
            call_command('process_outreach_queue', stdout=out)
        self.assertIn('Result: queue-empty', out.getvalue())
        self.assertIn('daily_limit: 10', out.getvalue())

    def test_celery_task_delegates(self):
        from outreach.tasks import process_outreach_queue
        with patch('outreach.tasks.process_queue', return_value='queue-empty'):
            self.assertEqual(process_outreach_queue(), 'queue-empty')
