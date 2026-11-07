from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import signing
from django.test import TestCase, override_settings
from kombu.exceptions import OperationalError

from leads.models import Lead
from outreach import gmail, humanizer
from outreach.models import OutreachMessage
from outreach.notify import build_notification, make_review_token, notify_draft
from outreach.signals import _queue_notification
from outreach.tasks import notify_draft_created

GMAIL_SETTINGS = {
    'GOOGLE_CLIENT_ID': 'cid',
    'GOOGLE_CLIENT_SECRET': 'secret',
    'GOOGLE_REFRESH_TOKEN': 'refresh',
    'OUTREACH_FROM_EMAIL': 'me@mydomain.com',
    'OUTREACH_NOTIFY_EMAIL': 'me@mydomain.com',
}
HUMAN_BODY = ("Hi James,\n\nI came across ABC Dental while looking at clinics in Manchester and put together "
              "a small concept site for you:\nhttps://demo.example.co.uk/abc-dental\n\nRegards,\nZubair")


class HumanizerTests(TestCase):
    def rules(self, subject, body):
        return {f['rule']: f['level'] for f in humanizer.check(subject, body)}

    def test_plain_human_email_is_clean(self):
        self.assertEqual(humanizer.check('A website concept for ABC Dental', HUMAN_BODY), [])

    def test_strong_tells_block(self):
        found = self.rules(
            'URGENT offer!!',
            "I hope this email finds you well. It's not just a website, but a growth engine — "
            "let's dive in. At its core, to be clear, act now \U0001F680",
        )
        for rule in ('dash', 'not-x-but-y', 'staged-opener', 'chatbot-residue', 'deep-saying',
                     'arguing-with-no-one', 'fake-urgency', 'emoji', 'shouting'):
            self.assertEqual(found.get(rule), 'block', rule)

    def test_weak_tells_warn(self):
        found = self.rules('Hello', "Our robust, renowned studio serves as a seamless partner! Really! “yes” "
                                    "It plays a key role.")
        for rule in ('ai-vocabulary', 'sales-language', 'avoiding-is', 'curly-quotes', 'exclamations',
                     'inflated-significance'):
            self.assertEqual(found.get(rule), 'warn', rule)

    def test_urls_are_ignored(self):
        self.assertEqual(humanizer.check('Hi', 'See https://x.co.uk/robust--vibrant-landscape'), [])

    def test_strict_mode_blocks_approval_and_lenient_mode_warns(self):
        user = get_user_model().objects.create_user(username='u', password='pw')
        lead = Lead.objects.create(owner=user, email='james@dental.co.uk', source='maps', is_verified=True)
        message = OutreachMessage.objects.create(owner=user, lead=lead, to_email=lead.email,
                                                 subject='Hi', body='I hope this email finds you well.')
        from outreach.services import content_warnings, preflight
        self.assertTrue(any('chatbot' in p or 'Stock chatbot' in p for p in preflight(message)))
        with override_settings(OUTREACH_HUMANIZER_STRICT=False):
            self.assertEqual(preflight(message), [])
            self.assertTrue(content_warnings(message.subject, message.body))


@override_settings(OUTREACH_BATCH_REVIEW=False, **GMAIL_SETTINGS)
class NotifyTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='u', password='pw')
        self.lead = Lead.objects.create(owner=self.user, email='james@dental.co.uk', source='maps',
                                        category='dentist', location='Manchester', is_verified=True)

    def make_draft(self, **kwargs):
        defaults = {'owner': self.user, 'lead': self.lead, 'to_email': self.lead.email,
                    'subject': 'A website concept for ABC Dental', 'body': HUMAN_BODY}
        defaults.update(kwargs)
        return OutreachMessage.objects.create(**defaults)

    @patch('outreach.mailer.send_message', return_value=('n1', 't1'))
    def test_new_draft_emails_owner_with_review_link(self, send):
        with self.captureOnCommitCallbacks(execute=True):
            message = self.make_draft()
        send.assert_called_once()
        to, subject, body = send.call_args.args
        self.assertEqual(to, 'me@mydomain.com')
        self.assertIn('[Review needed] james@dental.co.uk', subject)
        self.assertIn('Nothing is sent until you approve it', body)
        self.assertIn('http://localhost:8000/api/outreach/review/', body)
        self.assertIn("I won't contact you again.", body)
        self.assertFalse(send.call_args.kwargs['list_unsubscribe'])
        message.refresh_from_db()
        self.assertIsNotNone(message.notified_at)

    @patch('outreach.mailer.send_message')
    def test_only_new_drafts_notify(self, send):
        with self.captureOnCommitCallbacks(execute=True):
            message = self.make_draft(status='queued')
            message.subject = 'changed'
            message.save()
        send.assert_not_called()
        self.assertEqual(notify_draft_created(message.pk), 'not-a-draft')

    def test_notification_lists_problems_and_tips(self):
        message = self.make_draft(body='I hope this email finds you well. Our robust offer.')
        _, body = build_notification(message)
        self.assertIn('Must fix before it can be approved', body)
        self.assertIn('Humanizer suggestions', body)

    @patch('outreach.mailer.send_message', side_effect=gmail.GmailError('quota'))
    def test_failure_recorded(self, _send):
        message = self.make_draft()
        self.assertEqual(notify_draft(message), 'failed')
        message.refresh_from_db()
        self.assertEqual(message.notify_error, 'quota')

    def test_disabled_and_unconfigured(self):
        message = self.make_draft()
        with override_settings(OUTREACH_NOTIFY_ON_DRAFT=False):
            self.assertEqual(notify_draft(message), 'disabled')
        with override_settings(GOOGLE_REFRESH_TOKEN=''):
            self.assertEqual(notify_draft(message), 'gmail-not-configured')

    @patch('outreach.tasks.notify_draft_created.delay', side_effect=OperationalError('no broker'))
    @patch('outreach.mailer.send_message', return_value=('n1', 't1'))
    def test_falls_back_to_inline_when_celery_down(self, send, _delay):
        message = self.make_draft()
        _queue_notification(message.pk)
        send.assert_called_once()


class ReviewPageTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='u', password='pw')
        lead = Lead.objects.create(owner=self.user, email='james@dental.co.uk', source='maps', is_verified=True)
        self.message = OutreachMessage.objects.create(owner=self.user, lead=lead, to_email=lead.email,
                                                      subject='A concept for ABC Dental', body=HUMAN_BODY)
        self.url = f'/api/outreach/review/{make_review_token(self.message)}/'

    def test_get_shows_draft_without_changing_it(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'A concept for ABC Dental')
        self.assertContains(response, 'Approve and queue')
        self.assertContains(response, 'checks passed')
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, 'draft')

    def test_edit_then_approve(self):
        response = self.client.post(self.url, {'action': 'save', 'subject': 'New subject', 'body': 'Hi James,\r\nShort note.'})
        self.assertContains(response, 'Changes saved')
        self.message.refresh_from_db()
        self.assertEqual((self.message.subject, self.message.body), ('New subject', 'Hi James,\nShort note.'))

        response = self.client.post(self.url, {'action': 'approve', 'subject': 'New subject', 'body': 'Hi James,\nShort note.'})
        self.assertContains(response, 'Approved.')
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, 'queued')
        self.assertIsNotNone(self.message.approved_at)

        again = self.client.post(self.url, {'action': 'approve'})
        self.assertEqual(again.status_code, 409)

    def test_approve_blocked_by_humanizer(self):
        response = self.client.post(self.url, {'action': 'approve', 'subject': 'Hi',
                                               'body': "Hi — I hope this email finds you well."})
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'Must fix before approval', status_code=400)
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, 'draft')

    def test_reject(self):
        response = self.client.post(self.url, {'action': 'reject'})
        self.assertContains(response, 'Rejected')
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, 'cancelled')

    def test_bad_expired_and_missing_links(self):
        self.assertEqual(self.client.get('/api/outreach/review/garbage/').status_code, 404)
        with patch('outreach.review.read_review_token', side_effect=signing.SignatureExpired('old')):
            self.assertEqual(self.client.get(self.url).status_code, 410)
        self.message.delete()
        self.assertEqual(self.client.get(self.url).status_code, 404)
