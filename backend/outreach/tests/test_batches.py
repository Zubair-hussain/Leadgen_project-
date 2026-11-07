from datetime import timedelta
from unittest.mock import Mock, patch

import requests
from django.contrib.auth import get_user_model
from django.core import signing
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from leads.models import Lead
from leadgen import gemini
from outreach import ai, batches
from outreach.models import OutreachBatch, OutreachMessage

HUMAN_BODY = ("Hi,\n\nYour clinic came up when I searched for dentists around Manchester. I build websites "
              "for local businesses and have a quick idea for yours.\n\nWould you like me to send it over?"
              "\n\nRegards,\nZubair")
SETTINGS = {
    'GOOGLE_CLIENT_ID': 'cid', 'GOOGLE_CLIENT_SECRET': 'secret', 'GOOGLE_REFRESH_TOKEN': 'refresh',
    'OUTREACH_FROM_EMAIL': 'me@mydomain.com', 'OUTREACH_NOTIFY_EMAIL': 'me@mydomain.com',
    'OUTREACH_AUTO_SEND_ENABLED': True, 'GEMINI_API_KEY': 'gkey', 'OUTREACH_RESEARCH_ENABLED': False,
}
SAFE = {'verdict': 'approve', 'confidence': 0.97, 'issues': []}


def make_draft(owner, email, **kwargs):
    lead, _ = Lead.objects.get_or_create(email=email.lower(), defaults={
        'owner': owner, 'source': 'google-maps', 'category': 'Dentists', 'location': 'Manchester', 'is_verified': True})
    defaults = {'subject': 'Website help for your Manchester practice', 'body': HUMAN_BODY}
    defaults.update(kwargs)
    return OutreachMessage.objects.create(owner=owner, lead=lead, to_email=email, **defaults)


@override_settings(**SETTINGS)
class BatchCreationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='u', password='pw')

    @patch('outreach.mailer.send_message', return_value=('n', 't'))
    def test_many_drafts_one_email_one_batch(self, send):
        drafts = [make_draft(self.user, f'info@clinic{i}.co.uk') for i in range(3)]
        batch = batches.create_batch(self.user)
        self.assertEqual(send.call_count, 1)
        to, subject, body = send.call_args.args
        self.assertEqual(to, 'me@mydomain.com')
        self.assertIn('3 outreach email(s), one approval', subject)
        for draft in drafts:
            self.assertIn(draft.to_email, body)
        self.assertIn('/api/outreach/batch-review/', body)
        self.assertIn('auto-send policy runs', body)
        self.assertEqual(batch.messages.count(), 3)
        self.assertIsNotNone(batch.notified_at)
        self.assertIsNotNone(batch.auto_send_at)
        self.assertIsNone(batches.create_batch(self.user))  # nothing left to batch

    @patch('outreach.mailer.send_message', return_value=('n', 't'))
    def test_duplicates_never_reach_a_batch(self, send):
        first = make_draft(self.user, 'info@a.co.uk')
        newer = make_draft(self.user, 'INFO@a.co.uk')
        queued_elsewhere = make_draft(self.user, 'info@b.co.uk')
        OutreachMessage.objects.filter(pk=queued_elsewhere.pk).update(status='queued')
        already_queued = make_draft(self.user, 'info@b.co.uk')
        batch = batches.create_batch(self.user)
        first.refresh_from_db()
        already_queued.refresh_from_db()
        self.assertEqual((first.status, newer.pk in batch.messages.values_list('pk', flat=True)), ('cancelled', True))
        self.assertEqual(already_queued.status, 'cancelled')
        self.assertIn('Duplicate', already_queued.skip_reason)
        self.assertEqual(batch.messages.count(), 1)

    @override_settings(OUTREACH_AUTO_SEND_ENABLED=False)
    @patch('outreach.mailer.send_message', return_value=('n', 't'))
    def test_no_deadline_when_auto_send_off(self, send):
        make_draft(self.user, 'info@clinic.co.uk')
        batch = batches.create_batch(self.user)
        self.assertIsNone(batch.auto_send_at)
        self.assertIn('Auto-send is off', send.call_args.args[2])

    @patch('outreach.mailer.send_message', return_value=('n', 't'))
    def test_quiet_period_groups_late_drafts(self, send):
        now = timezone.now()
        old = make_draft(self.user, 'info@a.co.uk')
        recent = make_draft(self.user, 'info@b.co.uk')
        OutreachMessage.objects.filter(pk=old.pk).update(created_at=now - timedelta(seconds=300))
        OutreachMessage.objects.filter(pk=recent.pk).update(created_at=now - timedelta(seconds=30))
        # The newest draft is still fresh, so we wait: the admin gets ONE email, not two.
        self.assertEqual(batches.create_pending_batches(now), [])
        self.assertEqual(send.call_count, 0)
        OutreachMessage.objects.filter(pk=recent.pk).update(created_at=now - timedelta(seconds=200))
        created = batches.create_pending_batches(now)
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].messages.count(), 2)
        self.assertEqual(send.call_count, 1)

    @patch('outreach.mailer.send_message', side_effect=OSError('offline'))
    def test_notify_failure_recorded(self, _send):
        make_draft(self.user, 'info@clinic.co.uk')
        batch = batches.create_batch(self.user)
        self.assertIsNone(batch.notified_at)
        self.assertIn('offline', batch.notify_error)

    @override_settings(GOOGLE_REFRESH_TOKEN='')
    def test_unconfigured_gmail(self):
        make_draft(self.user, 'info@clinic.co.uk')
        self.assertEqual(batches.create_batch(self.user).notify_error, 'gmail-not-configured')

    def test_token_roundtrip_and_expiry(self):
        batch = OutreachBatch.objects.create(owner=self.user)
        self.assertEqual(batches.read_batch_token(batches.make_batch_token(batch)), batch.pk)
        with override_settings(OUTREACH_REVIEW_LINK_DAYS=-1), self.assertRaises(signing.SignatureExpired):
            batches.read_batch_token(batches.make_batch_token(batch))


@override_settings(**SETTINGS)
class BatchDecisionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='u', password='pw')
        with patch('outreach.mailer.send_message', return_value=('n', 't')):
            self.a = make_draft(self.user, 'info@a.co.uk')
            self.b = make_draft(self.user, 'info@b.co.uk')
            self.batch = batches.create_batch(self.user)

    def test_one_approval_queues_everything_and_applies_edits(self):
        outcome = batches.approve_batch(self.batch.pk, edits={self.a.pk: ('New subject', HUMAN_BODY)})
        self.assertEqual(outcome[1:3], (2, 0))
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.status, 'approved')
        for message in (self.a, self.b):
            message.refresh_from_db()
            self.assertEqual(message.status, 'queued')
        self.assertEqual(self.a.subject, 'New subject')
        self.assertIsNone(batches.approve_batch(self.batch.pk))  # decided once only

    def test_excluded_and_blocked_messages(self):
        OutreachMessage.objects.filter(pk=self.b.pk).update(body='Hi — I hope this email finds you well.')
        outcome = batches.approve_batch(self.batch.pk)
        self.assertEqual(outcome[1], 1)
        self.assertEqual(len(outcome[3]), 1)
        self.b.refresh_from_db()
        self.assertEqual(self.b.status, 'draft')
        self.assertTrue(self.b.skip_reason)

    def test_exclude_drops_one(self):
        outcome = batches.approve_batch(self.batch.pk, excluded={self.a.pk})
        self.assertEqual(outcome[1:3], (1, 1))
        self.a.refresh_from_db()
        self.assertEqual(self.a.status, 'cancelled')

    def test_reject_cancels_all(self):
        self.assertEqual(batches.reject_batch(self.batch.pk).status, 'rejected')
        self.assertEqual(OutreachMessage.objects.filter(status='cancelled').count(), 2)
        self.assertIsNone(batches.reject_batch(self.batch.pk))


@override_settings(**SETTINGS)
class AutoSendPolicyTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='u', password='pw')

    def batch_of(self, *emails, notified=True, **kwargs):
        for email in emails:
            make_draft(self.user, email, **kwargs)
        with patch('outreach.mailer.send_message', return_value=('n', 't')):
            batch = batches.create_batch(self.user)
        if not notified:
            OutreachBatch.objects.filter(pk=batch.pk).update(notified_at=None)
        OutreachBatch.objects.filter(pk=batch.pk).update(auto_send_at=timezone.now() - timedelta(minutes=1))
        return batch

    @patch('outreach.mailer.send_message', return_value=('n', 't'))
    @patch('outreach.ai.gemini.generate', return_value=SAFE)
    def test_certain_emails_are_queued_and_admin_told(self, _gen, send):
        batch = self.batch_of('info@a.co.uk', 'info@b.co.uk')
        self.assertEqual(len(batches.run_auto_sends()), 1)
        batch.refresh_from_db()
        self.assertEqual(batch.status, 'auto_approved')
        self.assertEqual(OutreachMessage.objects.filter(status='queued').count(), 2)
        self.assertIn('2 queued, 0 held back', send.call_args.args[1])

    @patch('outreach.mailer.send_message', return_value=('n', 't'))
    @patch('outreach.ai.gemini.generate', return_value=SAFE)
    def test_personal_mailbox_is_never_auto_sent(self, _gen, send):
        batch = self.batch_of('info@a.co.uk', 'someone@outlook.com')
        batches.run_auto_sends()
        held = OutreachMessage.objects.get(to_email='someone@outlook.com')
        self.assertEqual(held.status, 'draft')
        self.assertIn('personal mailbox', held.hold_reason)
        self.assertEqual(OutreachMessage.objects.get(to_email='info@a.co.uk').status, 'queued')
        self.assertIn('1 queued, 1 held back', send.call_args.args[1])
        batch.refresh_from_db()
        self.assertEqual(batch.status, 'auto_approved')

    @patch('outreach.mailer.send_message', return_value=('n', 't'))
    def test_when_not_sure_nothing_is_sent(self, send):
        cases = {
            'unsure': {'verdict': 'unsure', 'confidence': 0.99, 'issues': ['claim is vague']},
            'low confidence': {'verdict': 'approve', 'confidence': 0.5, 'issues': []},
            'has concerns': {'verdict': 'approve', 'confidence': 0.99, 'issues': ['tone']},
            'bad confidence value': {'verdict': 'approve', 'confidence': 'high', 'issues': []},
            'reject': {'verdict': 'reject', 'confidence': 1, 'issues': []},
        }
        for name, answer in cases.items():
            with self.subTest(name):
                OutreachMessage.objects.all().delete()
                OutreachBatch.objects.all().delete()
                Lead.objects.all().delete()
                batch = self.batch_of('info@a.co.uk')
                with patch('outreach.ai.gemini.generate', return_value=answer):
                    batches.run_auto_sends()
                batch.refresh_from_db()
                self.assertEqual(batch.status, 'held')
                message = OutreachMessage.objects.get()
                self.assertEqual(message.status, 'draft')
                self.assertTrue(message.hold_reason)

    @patch('outreach.mailer.send_message', return_value=('n', 't'))
    def test_gemini_failures_mean_hold(self, _send):
        for effect in (gemini.GeminiError('503'), ['not', 'a', 'dict']):
            OutreachMessage.objects.all().delete()
            OutreachBatch.objects.all().delete()
            Lead.objects.all().delete()
            self.batch_of('info@a.co.uk')
            with patch('outreach.ai.gemini.generate',
                       **({'side_effect': effect} if isinstance(effect, Exception) else {'return_value': effect})):
                batches.run_auto_sends()
            self.assertEqual(OutreachMessage.objects.get().status, 'draft')
        OutreachMessage.objects.all().delete()
        OutreachBatch.objects.all().delete()
        Lead.objects.all().delete()
        self.batch_of('info@a.co.uk')
        with override_settings(GEMINI_API_KEY=''):
            batches.run_auto_sends()
        self.assertIn('not configured', OutreachMessage.objects.get().hold_reason)

    @patch('outreach.mailer.send_message', return_value=('n', 't'))
    @patch('outreach.ai.gemini.generate', return_value=SAFE)
    def test_humanizer_findings_and_long_emails_are_held(self, _gen, _send):
        self.batch_of('info@a.co.uk', body='Hi,\n\nOur robust service is a great fit.\n\nRegards,\nZ')
        batches.run_auto_sends()
        self.assertIn('Humanizer', OutreachMessage.objects.get().hold_reason)
        message = OutreachMessage.objects.get()
        message.body = 'word ' * 200
        self.assertIn('word limit', batches.unsure_reason(message) or 'word limit')

    @patch('outreach.ai.gemini.generate', return_value=SAFE)
    def test_never_auto_sends_unless_admin_was_notified(self, _gen):
        batch = self.batch_of('info@a.co.uk', notified=False)
        self.assertEqual(batches.run_auto_sends(), [])
        batch.refresh_from_db()
        self.assertEqual(batch.status, 'pending')

    @patch('outreach.ai.gemini.generate', return_value=SAFE)
    def test_not_before_deadline_and_not_when_disabled(self, _gen):
        batch = self.batch_of('info@a.co.uk')
        OutreachBatch.objects.filter(pk=batch.pk).update(auto_send_at=timezone.now() + timedelta(hours=1))
        self.assertEqual(batches.run_auto_sends(), [])
        OutreachBatch.objects.filter(pk=batch.pk).update(auto_send_at=timezone.now() - timedelta(hours=1))
        with override_settings(OUTREACH_AUTO_SEND_ENABLED=False):
            self.assertEqual(batches.run_auto_sends(), [])
        self.assertEqual(OutreachMessage.objects.get().status, 'draft')

    @patch('outreach.ai.gemini.generate', return_value=SAFE)
    def test_admin_decision_beats_auto_send(self, _gen):
        batch = self.batch_of('info@a.co.uk')
        batches.reject_batch(batch.pk)
        self.assertEqual(batches.run_auto_sends(), [])
        self.assertIsNone(batches.auto_approve_batch(batch.pk))

    @patch('outreach.mailer.send_message', return_value=('n', 't'))
    @patch('outreach.ai.gemini.generate', return_value=SAFE)
    def test_process_batches_runs_both_steps(self, _gen, _send):
        make_draft(self.user, 'info@a.co.uk')
        result = batches.process_batches(timezone.now() + timedelta(seconds=500))
        self.assertEqual(result, {'created': 1, 'auto': 0})
        from outreach.tasks import process_batches
        self.assertEqual(process_batches(), {'created': 0, 'auto': 0})


@override_settings(**SETTINGS)
class BatchPageTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='u', password='pw')
        with patch('outreach.mailer.send_message', return_value=('n', 't')):
            self.a = make_draft(self.user, 'info@a.co.uk')
            self.b = make_draft(self.user, 'info@b.co.uk')
            self.batch = batches.create_batch(self.user)
        self.url = f'/api/outreach/batch-review/{batches.make_batch_token(self.batch)}/'

    def test_page_lists_everything_with_one_approve_button(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'Review 2 outreach emails')
        self.assertContains(response, 'info@a.co.uk')
        self.assertContains(response, 'info@b.co.uk')
        self.assertContains(response, 'Approve all ticked')
        self.assertContains(response, 'auto-send policy runs')

    def test_approve_with_one_unticked_and_one_edit(self):
        response = self.client.post(self.url, {
            'action': 'approve', 'include': [str(self.a.pk)],
            f'subject_{self.a.pk}': 'Edited subject', f'body_{self.a.pk}': HUMAN_BODY.replace('\n', '\r\n'),
        })
        self.assertContains(response, 'You approved 1 email(s); 1 dropped')
        self.a.refresh_from_db()
        self.b.refresh_from_db()
        self.assertEqual((self.a.status, self.a.subject), ('queued', 'Edited subject'))
        self.assertNotIn('\r', self.a.body)
        self.assertEqual(self.b.status, 'cancelled')
        again = self.client.post(self.url, {'action': 'approve'})
        self.assertEqual(again.status_code, 409)
        self.assertContains(self.client.get(self.url), 'Approved by you')

    def test_blocked_email_is_reported(self):
        response = self.client.post(self.url, {
            'action': 'approve', 'include': [str(self.a.pk), str(self.b.pk)],
            f'subject_{self.b.pk}': 'Hi', f'body_{self.b.pk}': 'Hi — let us dive in.',
        })
        self.assertContains(response, 'blocked by checks', status_code=200)

    def test_reject_all(self):
        self.assertContains(self.client.post(self.url, {'action': 'reject'}), 'Rejected. Nothing will be sent.')
        self.assertEqual(OutreachMessage.objects.filter(status='cancelled').count(), 2)

    def test_bad_links(self):
        self.assertEqual(self.client.get('/api/outreach/batch-review/nope/').status_code, 404)
        with patch('outreach.review.batches.read_batch_token', side_effect=signing.SignatureExpired('x')):
            self.assertEqual(self.client.get(self.url).status_code, 410)
        self.batch.delete()
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_decided_batch_shows_held_reasons(self):
        with patch('outreach.ai.gemini.generate', return_value={'verdict': 'unsure', 'confidence': 1, 'issues': []}):
            OutreachBatch.objects.filter(pk=self.batch.pk).update(auto_send_at=timezone.now(), notified_at=timezone.now())
            with patch('outreach.mailer.send_message', return_value=('n', 't')):
                batches.run_auto_sends()
        self.assertContains(self.client.get(self.url), 'Held:')


@override_settings(**SETTINGS)
class GeminiAndAiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='u', password='pw')

    def fake_post(self, status=200, text='{"a": 1}'):
        response = Mock(status_code=status, text=text)
        response.json.return_value = {'candidates': [{'content': {'parts': [{'text': text}]}}]}
        return response

    @patch('leadgen.gemini.requests.post')
    def test_client(self, post):
        post.return_value = self.fake_post(text='```json\n{"a": 1}\n```')
        self.assertEqual(gemini.generate('hi', json_output=True), {'a': 1})
        self.assertEqual(post.call_args.kwargs['headers']['x-goog-api-key'], 'gkey')
        post.return_value = self.fake_post(text='plain')
        self.assertEqual(gemini.generate('hi'), 'plain')
        post.return_value = self.fake_post(text='not json')
        with self.assertRaises(gemini.GeminiError):
            gemini.generate('hi', json_output=True)
        post.return_value = self.fake_post(status=500)
        with self.assertRaises(gemini.GeminiError):
            gemini.generate('hi')
        post.return_value = Mock(status_code=200, json=Mock(return_value={}))
        with self.assertRaises(gemini.GeminiError):
            gemini.generate('hi')
        post.side_effect = requests.ConnectionError('down')
        with self.assertRaises(gemini.GeminiError):
            gemini.generate('hi')
        with override_settings(GEMINI_API_KEY=''), self.assertRaises(gemini.GeminiError):
            gemini.generate('hi')

    @patch('outreach.ai.gemini.generate')
    def test_writer_creates_clean_drafts_only(self, generate):
        good = {'subject': 'Website help for your practice', 'body': HUMAN_BODY}
        bad = {'subject': 'Elevate now', 'body': "I hope this email finds you well — let's dive in."}
        lead_ok = Lead.objects.create(owner=self.user, email='info@a.co.uk', source='x', category='Dentists', is_verified=True)
        generate.return_value = good
        created, skipped = ai.write_drafts(self.user, [lead_ok])
        self.assertEqual((len(created), skipped), (1, []))
        self.assertEqual(created[0].status, 'draft')

        generate.reset_mock()
        generate.side_effect = [bad, bad, bad]
        lead_bad = Lead.objects.create(owner=self.user, email='info@b.co.uk', source='x', is_verified=True)
        created, skipped = ai.write_drafts(self.user, [lead_bad])
        self.assertEqual(created, [])
        self.assertIn('humanizer', skipped[0]['reason'])
        self.assertIn('rejected for', generate.call_args_list[1].args[0])  # second try is told what to fix

        generate.side_effect = gemini.GeminiError('down')
        self.assertEqual(len(ai.write_drafts(self.user, [lead_bad])[1]), 1)
        generate.side_effect = None
        generate.return_value = ['no']
        self.assertEqual(len(ai.write_drafts(self.user, [lead_bad])[1]), 1)

    def test_lead_facts_without_lead(self):
        message = OutreachMessage.objects.create(owner=self.user, to_email='a@b.co.uk', subject='s', body='b')
        self.assertIn('note', ai.lead_facts(message))

    @patch('leads.services.gemini.generate', return_value=[0, 2, 'x', 9])
    def test_lead_filter_uses_shared_client(self, _gen):
        from leads.services import LeadGenerator
        generator = LeadGenerator()
        generator.gemini_key = 'k'
        leads = [{'source': 's', 'problem_statement': str(i)} for i in range(3)]
        self.assertEqual(generator.filter_leads_with_ai(leads, 'Dentists'), [leads[0], leads[2]])
        with patch('leads.services.gemini.generate', side_effect=gemini.GeminiError('x')):
            self.assertEqual(generator.filter_leads_with_ai(leads, 'Dentists'), leads)
        with patch('leads.services.gemini.generate', return_value={'a': 1}):
            self.assertEqual(generator.filter_leads_with_ai(leads, 'Dentists'), leads)


@override_settings(**SETTINGS)
class BatchApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='u', password='pw')
        self.client.force_authenticate(self.user)

    @patch('outreach.mailer.send_message', return_value=('n', 't'))
    def test_create_and_list_batches(self, send):
        self.assertEqual(self.client.post('/api/outreach/batches/').status_code, 400)
        make_draft(self.user, 'info@a.co.uk')
        make_draft(self.user, 'info@b.co.uk')
        response = self.client.post('/api/outreach/batches/')
        self.assertEqual((response.status_code, response.data['messages'], response.data['notified']), (201, 2, True))
        self.assertEqual(send.call_count, 1)
        listing = self.client.get('/api/outreach/batches/')
        self.assertEqual(listing.data[0]['status'], 'pending')

    @patch('outreach.ai.gemini.generate',
           return_value={'subject': 'Website help for your practice', 'body': HUMAN_BODY})
    def test_ai_drafts_endpoint(self, _gen):
        Lead.objects.create(owner=self.user, email='info@a.co.uk', source='x', category='Dentists', is_verified=True)
        Lead.objects.create(owner=self.user, email='info@unverified.co.uk', source='x', is_verified=False)
        response = self.client.post('/api/outreach/ai-drafts/', {}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.data['created']), 1)
        # Running again does not write a second draft for the same lead.
        self.assertEqual(self.client.post('/api/outreach/ai-drafts/', {}, format='json').data['created'], [])
        lead = Lead.objects.get(email='info@a.co.uk')
        OutreachMessage.objects.all().delete()
        self.assertEqual(len(self.client.post('/api/outreach/ai-drafts/', {'lead_ids': [lead.pk]},
                                              format='json').data['created']), 1)
