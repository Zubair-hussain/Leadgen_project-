import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from leads.models import Lead
from outreach import autopilot, branding, mailer, mime, report, resend_client, unsubscribe, webhooks
from outreach.models import OutreachMessage, Suppression

SUNDAY_EVENING = timezone.make_aware(datetime(2026, 11, 15, 19, 0), dt_timezone.utc)   # Sunday 19:00 UTC
SUNDAY_MORNING = timezone.make_aware(datetime(2026, 11, 15, 9, 0), dt_timezone.utc)
PKT_MORNING = timezone.make_aware(datetime(2026, 11, 16, 5, 0), dt_timezone.utc)  # Mon 10:00 Pakistan
RESEND = {'OUTREACH_TRANSPORT': 'resend', 'RESEND_API_KEY': 're_test', 'OUTREACH_FROM_EMAIL': 'hello@zubairhussain.xyz',
          'OUTREACH_FROM_NAME': 'Zubair Hussain', 'OUTREACH_REPLY_TO': 'zubair@zubairhussain.xyz'}


def make_user(name='owner'):
    return get_user_model().objects.create_user(username=name, email=f'{name}@example.com', password='pw')


@override_settings(**RESEND)
class ResendTransportTests(TestCase):
    def test_mailer_picks_resend(self):
        self.assertEqual(mailer.transport(), 'resend')
        self.assertTrue(mailer.is_configured())

    def test_payload_has_reply_to_threading_and_unsubscribe(self):
        payload = resend_client.build_payload('a@b.com', 'hi', 'body', html='<p>body</p>', message_id='<m1@x>',
                                              in_reply_to='<m0@x>')
        self.assertEqual(payload['from'], 'Zubair Hussain <hello@zubairhussain.xyz>')
        self.assertEqual(payload['reply_to'], ['zubair@zubairhussain.xyz'])
        self.assertEqual(payload['headers']['In-Reply-To'], '<m0@x>')
        self.assertIn('mailto:zubair@zubairhussain.xyz', payload['headers']['List-Unsubscribe'])
        self.assertEqual((payload['text'], payload['html']), ('body', '<p>body</p>'))

    @patch('outreach.resend_client.requests.post')
    def test_send_returns_resend_id(self, post):
        post.return_value = MagicMock(status_code=200, json=lambda: {'id': 'em_123'})
        self.assertEqual(mailer.send_message('a@b.com', 'hi', 'body'), ('em_123', ''))
        self.assertEqual(post.call_args.kwargs['headers']['Authorization'], 'Bearer re_test')

    @patch('outreach.resend_client.requests.post')
    def test_refusal_raises_a_mailer_error(self, post):
        post.return_value = MagicMock(status_code=403, json=lambda: {'message': 'domain not verified'})
        with self.assertRaises(mailer.ERRORS) as ctx:
            mailer.send_message('a@b.com', 'hi', 'body')
        self.assertIn('domain not verified', str(ctx.exception))

    def test_smtp_mime_gets_reply_to_too(self):
        msg = mime.build_mime('a@b.com', 'hi', 'body')
        self.assertEqual(msg['Reply-To'], 'zubair@zubairhussain.xyz')


@override_settings(OUTREACH_AUTOPILOT_ENABLED=True, OUTREACH_AUTOPILOT_OWNER='owner',
                   OUTREACH_AUTOPILOT_TARGETS='Dentists|Leeds, UK; plumbers | Austin, TX',
                   OUTREACH_AUTOPILOT_DRAFTS_PER_DAY=3, OUTREACH_AUTOPILOT_DRAFTS_PER_RUN=2)
class AutopilotTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def lead(self, email, country='GB'):
        return Lead.objects.create(owner=self.user, email=email, source='google-maps', category='Dentists',
                                   location='Leeds', country=country, is_verified=True)

    def test_targets_parse(self):
        self.assertEqual(autopilot.targets(), [('Dentists', 'Leeds, UK'), ('plumbers', 'Austin, TX')])

    @override_settings(OUTREACH_AUTOPILOT_ENABLED=False)
    def test_disabled(self):
        self.assertEqual(autopilot.run_autopilot(), 'disabled')

    @patch('outreach.ai.write_drafts')
    @patch('leads.services.LeadGenerator')
    def test_hunts_once_a_day_then_drafts(self, generator, write_drafts):
        generator.return_value.generate_leads.return_value = [{'id': 1}]
        now = PKT_MORNING
        self.assertIn('hunted 1 new leads', autopilot.run_autopilot(now))
        self.assertEqual(generator.return_value.generate_leads.call_args.kwargs['owner'], self.user)

        good, other = self.lead('info@clinic.co.uk'), self.lead('team@smiles.co.uk')
        self.lead('someone@gmail.com')            # UK personal mailbox: never drafted
        self.lead('praxis@zahn.de', country='DE')  # blocked country
        write_drafts.side_effect = lambda user, leads: (
            [OutreachMessage.objects.create(owner=user, lead=lead, to_email=lead.email, subject='s', body='b')
             for lead in leads], [])
        self.assertEqual(autopilot.run_autopilot(now + timedelta(minutes=30)), 'drafted 2, skipped 0')
        self.assertEqual({lead.email for lead in write_drafts.call_args.args[1]}, {good.email, other.email})
        self.assertEqual(autopilot.run_autopilot(now + timedelta(hours=1)), 'no-new-leads-to-draft')
        generator.return_value.generate_leads.assert_called_once()

    @patch('outreach.ai.write_drafts')
    @patch('outreach.autopilot._claim_hunt', return_value=False)
    def test_skipped_leads_are_parked(self, _claim, write_drafts):
        lead = self.lead('info@clinic.co.uk')
        write_drafts.return_value = ([], [{'lead_id': lead.pk, 'email': lead.email, 'reason': 'closed'}])
        self.assertEqual(autopilot.run_autopilot(PKT_MORNING), 'drafted 0, skipped 1')
        self.assertEqual(OutreachMessage.objects.get(lead=lead).status, 'cancelled')
        self.assertEqual(autopilot.run_autopilot(PKT_MORNING), 'no-new-leads-to-draft')

    def test_waits_until_seven_pakistan_time(self):
        early = timezone.make_aware(datetime(2026, 11, 16, 1, 30), dt_timezone.utc)  # 06:30 PKT
        self.assertTrue(autopilot.run_autopilot(early).startswith('waiting-until-07:00'))
        marker_free = autopilot._claim_hunt(early + timedelta(hours=1))  # 07:30 PKT
        self.assertTrue(marker_free)
        self.assertFalse(autopilot._claim_hunt(early + timedelta(hours=20)))  # still same PKT day
        self.assertTrue(autopilot._claim_hunt(early + timedelta(days=1, hours=1)))  # next day 07:30

    @override_settings(OUTREACH_AUTOPILOT_OWNER='nobody')
    def test_unknown_owner(self):
        self.assertIn('owner-not-found', autopilot.run_autopilot())


@override_settings(OUTREACH_REPORT_TIMEZONE='UTC', OUTREACH_REPORT_WEEKDAY=6, OUTREACH_REPORT_HOUR=18,
                   OUTREACH_NOTIFY_EMAIL='me@example.com', OUTREACH_WEEKLY_REPORT_ENABLED=True, **RESEND)
class WeeklyReportTests(TestCase):
    def setUp(self):
        self.user = make_user()
        base = SUNDAY_EVENING - timedelta(days=2)
        for i in range(3):
            OutreachMessage.objects.create(owner=self.user, to_email=f'p{i}@shop.com', subject='s', body='b',
                                           status='sent', sent_at=base, replied_at=base if i == 0 else None)
        OutreachMessage.objects.create(owner=self.user, to_email='old@shop.com', subject='s', body='b',
                                       status='sent', sent_at=SUNDAY_EVENING - timedelta(days=9))

    def test_counts_only_the_last_seven_days(self):
        stats = report.collect(SUNDAY_EVENING)
        self.assertEqual((stats['sent_total'], stats['replies'], stats['all_time_sent']), (3, 1, 4))
        self.assertEqual(stats['reply_rate'], 33.3)
        subject, body = report.build(stats)
        self.assertIn('3 emails sent', subject)
        self.assertIn('Replies:            1', body)

    @patch('outreach.report.mailer.send_message', return_value=('id', ''))
    def test_sends_once_on_sunday_evening(self, send):
        self.assertEqual(report.weekly_report(SUNDAY_MORNING), 'not-due')
        self.assertEqual(report.weekly_report(SUNDAY_MORNING + timedelta(days=1, hours=10)), 'not-due')  # Monday
        self.assertEqual(report.weekly_report(SUNDAY_EVENING), 'sent')
        self.assertEqual(report.weekly_report(SUNDAY_EVENING + timedelta(minutes=5)), 'already-sent')
        self.assertEqual(send.call_args.args[0], 'me@example.com')
        self.assertEqual(report.weekly_report(SUNDAY_EVENING + timedelta(days=7)), 'sent')

    @patch('outreach.report.mailer.send_message', side_effect=resend_client.ResendError('down'))
    def test_failure_retries_within_the_hour(self, _send):
        self.assertTrue(report.weekly_report(SUNDAY_EVENING).startswith('failed'))
        self.assertEqual(report.weekly_report(SUNDAY_EVENING + timedelta(minutes=10)), 'already-sent')
        with patch('outreach.report.mailer.send_message', return_value=('id', '')):
            self.assertEqual(report.weekly_report(SUNDAY_EVENING + timedelta(minutes=61)), 'sent')


SECRET = 'whsec_' + base64.b64encode(b'webhook-secret-key').decode()


def signed(body, secret=SECRET, ts=None):
    ts = str(ts or int(time.time()))
    key = base64.b64decode(secret.split('_', 1)[1])
    sig = base64.b64encode(hmac.new(key, f'msg_1.{ts}.'.encode() + body, hashlib.sha256).digest()).decode()
    return {'HTTP_SVIX_ID': 'msg_1', 'HTTP_SVIX_TIMESTAMP': ts, 'HTTP_SVIX_SIGNATURE': f'v1,{sig}'}


@override_settings(RESEND_WEBHOOK_SECRET=SECRET)
class ResendWebhookTests(TestCase):
    url = '/api/outreach/webhooks/resend/'

    def setUp(self):
        self.user = make_user()
        self.sent = OutreachMessage.objects.create(owner=self.user, to_email='Dead@Shop.com', subject='s', body='b',
                                                   status='sent', gmail_message_id='em_9')
        self.queued = OutreachMessage.objects.create(owner=self.user, to_email='dead@shop.com', subject='s2',
                                                     body='b', status='queued', parent=self.sent, sequence_step=1)

    def post(self, event, **headers):
        body = json.dumps(event).encode()
        return self.client.post(self.url, body, content_type='application/json', **(headers or signed(body)))

    def test_bad_signature_is_refused(self):
        body = json.dumps({'type': 'email.bounced'}).encode()
        self.assertEqual(self.post({'type': 'email.bounced'}, **signed(body + b'x')).status_code, 401)
        self.assertEqual(self.post({'type': 'email.bounced'}, **signed(body, ts=1000)).status_code, 401)

    def test_bounce_suppresses_and_cancels_followups(self):
        response = self.post({'type': 'email.bounced', 'data': {'email_id': 'em_9'}})
        self.assertEqual(response.json(), {'result': 'suppressed'})
        self.assertEqual(Suppression.objects.get(owner=self.user).reason, 'bounce')
        self.sent.refresh_from_db()
        self.queued.refresh_from_db()
        self.assertIsNotNone(self.sent.bounced_at)
        self.assertEqual(self.queued.status, 'cancelled')

    def test_complaint_and_other_events(self):
        self.assertEqual(self.post({'type': 'email.delivered', 'data': {'email_id': 'em_9'}}).json()['result'],
                         'ignored')
        self.post({'type': 'email.complained', 'data': {'email_id': 'em_9'}})
        self.assertEqual(Suppression.objects.get(owner=self.user).reason, 'complaint')
        self.assertTrue(webhooks.verify_signature(SECRET, 'msg_1', signed(b'{}')['HTTP_SVIX_TIMESTAMP'],
                                                  signed(b'{}')['HTTP_SVIX_SIGNATURE'], b'{}'))


@override_settings(OUTREACH_REVIEW_BASE_URL='https://api.example.com', **RESEND)
class OneClickUnsubscribeTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.sent = OutreachMessage.objects.create(owner=self.user, to_email='Boss@Shop.com', subject='s', body='b',
                                                   status='sent')
        self.queued = OutreachMessage.objects.create(owner=self.user, to_email='boss@shop.com', subject='s2',
                                                     body='b', status='queued', parent=self.sent, sequence_step=1)
        self.url = unsubscribe.url_for(self.sent)

    def test_headers_follow_rfc_8058(self):
        payload = resend_client.build_payload('a@b.com', 'hi', 'body', unsubscribe_url=self.url)
        self.assertTrue(payload['headers']['List-Unsubscribe'].startswith(f'<{self.url}>, <mailto:'))
        self.assertEqual(payload['headers']['List-Unsubscribe-Post'], 'List-Unsubscribe=One-Click')
        msg = mime.build_mime('a@b.com', 'hi', 'body', unsubscribe_url=self.url)
        self.assertEqual(msg['List-Unsubscribe-Post'], 'List-Unsubscribe=One-Click')

    @override_settings(OUTREACH_REVIEW_BASE_URL='http://localhost:8000')
    def test_no_public_url_means_mailto_only(self):
        self.assertEqual(unsubscribe.url_for(self.sent), '')

    def test_get_only_confirms_post_unsubscribes(self):
        path = self.url.replace('https://api.example.com', '')
        self.assertContains(self.client.get(path), 'Unsubscribe</button>')
        self.assertFalse(Suppression.objects.exists())
        response = self.client.post(path, 'List-Unsubscribe=One-Click',
                                    content_type='application/x-www-form-urlencoded')
        self.assertContains(response, 'You are unsubscribed.')
        self.assertContains(self.client.get(path), 'You are unsubscribed.')  # opening the link again shows the label
        self.assertEqual(Suppression.objects.get().email, 'boss@shop.com')
        self.queued.refresh_from_db()
        self.assertEqual(self.queued.status, 'cancelled')
        self.assertEqual(self.client.post('/api/outreach/unsubscribe/forged/').status_code, 400)

    def test_email_shows_booking_button_services_and_unsubscribe(self):
        text, html = branding.compose('hi', 'Hello there', unsubscribe_url=self.url)
        self.assertIn('Book a 15-min call', html)
        self.assertIn('calendly-booking-navy.vercel.app', html)
        self.assertIn('Website security checks', html)
        self.assertIn(self.url, html)
        self.assertIn(f'Unsubscribe with one click: {self.url}', text)

    @override_settings(OUTREACH_SEND_TIMEZONE='Asia/Karachi', OUTREACH_SEND_HOUR_START=7, OUTREACH_SEND_HOUR_END=11,
                       OUTREACH_WEEKDAYS_ONLY=True)
    def test_single_send_timezone(self):
        from outreach.services import in_send_window
        self.assertTrue(in_send_window(PKT_MORNING, region='US'))  # 10:00 PKT for everyone
        self.assertFalse(in_send_window(PKT_MORNING + timedelta(hours=2), region='US'))  # 12:00 PKT


class SendTestEmailCommandTests(TestCase):
    @override_settings(OUTREACH_NOTIFY_EMAIL='me@example.com', OUTREACH_REVIEW_BASE_URL='https://api.example.com',
                       **RESEND)
    @patch('outreach.resend_client.requests.post')
    def test_sends_branded_sample_to_me(self, post):
        from io import StringIO
        from django.core.management import call_command
        post.return_value = MagicMock(status_code=200, json=lambda: {'id': 'em_1'})
        out = StringIO()
        call_command('send_test_email', stdout=out)
        payload = post.call_args.kwargs['json']
        self.assertEqual(payload['to'], ['me@example.com'])
        self.assertIn('Book a 15-min call', payload['html'])
        self.assertEqual(payload['headers']['List-Unsubscribe-Post'], 'List-Unsubscribe=One-Click')
        self.assertIn('Sent via resend', out.getvalue())
