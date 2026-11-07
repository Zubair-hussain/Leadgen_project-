from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import requests
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from leads.models import Lead
from outreach import ai, batches, research
from outreach.models import LeadResearch, OutreachMessage
from outreach.services import process_queue

WORK_TIME = timezone.make_aware(datetime(2026, 10, 13, 10, 0))  # Tuesday 10:00
SETTINGS = {
    'SERPAPI_KEY': 'skey', 'OUTREACH_RESEARCH_ENABLED': True, 'GOOGLE_CLIENT_ID': 'c', 'GOOGLE_CLIENT_SECRET': 's',
    'GOOGLE_REFRESH_TOKEN': 'r', 'OUTREACH_FROM_EMAIL': 'me@mydomain.com', 'OUTREACH_DRY_RUN': False,
    'GEMINI_API_KEY': 'gkey',
}
GOOD_BODY = ("Hi,\n\nYour 301 reviews in Manchester show patients trust you. I build quick, simple websites for "
             "local clinics, and I have an idea for a booking page that fits yours.\n\n"
             "Would you like me to send it over?\n\nRegards,\nZubair")
PLACE = {'title': 'Manchester Dental Practice', 'rating': 4.1, 'reviews': 301, 'address': '2-4 Exchange St',
         'website': 'https://www.manchesterdentalpractice.co.uk/', 'type': ['Dental clinic', 'Dentist'],
         'open_state': 'Closed ⋅ Opens 9 AM Mon'}


def serp(place=None, results=None, status=200, error=None):
    payload = {}
    if place is not None:
        payload['place_results'] = place
    if results is not None:
        payload['local_results'] = results
    if error:
        payload['error'] = error
    return Mock(status_code=status, json=Mock(return_value=payload))


def make_lead(owner, email='info@manchesterdentalpractice.co.uk', **kwargs):
    defaults = {
        'owner': owner, 'source': 'google-maps', 'category': 'Dentists', 'is_verified': True,
        'location': '2-4 Exchange St, Manchester', 'link': 'https://www.manchesterdentalpractice.co.uk/',
        'problem_statement': 'Local business: Manchester Dental Practice. May need services.',
    }
    defaults.update(kwargs)
    return Lead.objects.create(email=email, **defaults)


@override_settings(**SETTINGS)
class LookupTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='u', password='pw')
        self.lead = make_lead(self.user)

    @patch('outreach.research.requests.get')
    def test_matched_by_website(self, get):
        get.return_value = serp(place=PLACE)
        status, data, note = research.lookup(self.lead)
        self.assertEqual((status, note), ('ok', ''))
        self.assertEqual((data['name'], data['rating'], data['reviews'], data['has_website']),
                         ('Manchester Dental Practice', 4.1, 301, True))
        self.assertFalse(data['website_changed'])
        query = get.call_args.kwargs['params']['q']
        self.assertEqual(query, 'Manchester Dental Practice, 2-4 Exchange St, Manchester')

    @patch('outreach.research.requests.get')
    def test_picks_the_right_candidate_and_detects_changed_website(self, get):
        other = dict(PLACE, title='Other Clinic', website='https://other.example.org/')
        mine = dict(PLACE, website='https://manchesterdentalpractice.co.uk/new-site')
        get.return_value = serp(results=[other, mine])
        status, data, _ = research.lookup(self.lead)
        self.assertEqual(status, 'ok')
        self.assertEqual(data['website'], mine['website'])
        moved = dict(PLACE, website='https://newdomain.co.uk/')
        get.return_value = serp(results=[moved])  # same name, different site
        status, data, _ = research.lookup(self.lead)
        self.assertEqual((status, data['website_changed']), ('ok', True))

    @patch('outreach.research.requests.get')
    def test_no_confident_match(self, get):
        get.return_value = serp(results=[dict(PLACE, title='Different', website='https://x.example.org')])
        self.assertEqual(research.lookup(self.lead)[0], 'no_match')
        get.return_value = serp()
        self.assertEqual(research.lookup(self.lead)[0], 'no_match')

    @patch('outreach.research.requests.get')
    def test_closed_businesses(self, get):
        for field, value in (('open_state', 'Permanently closed'), ('extensions', ['Temporarily closed']),
                             ('permanently_closed', True)):
            get.return_value = serp(place=dict(PLACE, **{field: value}))
            status, data, note = research.lookup(self.lead)
            self.assertEqual(status, 'closed')
            self.assertIn('closed', note)
            self.assertIn('closed', data['closed'])

    @patch('outreach.research.requests.get')
    def test_errors_never_raise(self, get):
        get.side_effect = requests.ConnectionError('down')
        self.assertEqual(research.lookup(self.lead)[0], 'error')
        get.side_effect = None
        get.return_value = serp(status=429, error='Your account has run out of searches.')
        self.assertIn('run out', research.lookup(self.lead)[2])
        get.return_value = Mock(status_code=200, json=Mock(side_effect=ValueError('bad json')))
        self.assertEqual(research.lookup(self.lead)[0], 'error')
        with override_settings(SERPAPI_KEY=''):
            self.assertEqual(research.lookup(self.lead)[2], 'SERPAPI_KEY is not set.')

    @patch('outreach.research.requests.get', return_value=serp(place=PLACE))
    def test_falls_back_to_domain_when_no_name(self, get):
        lead = make_lead(self.user, email='x@manchesterdentalpractice.co.uk', problem_statement='', location='')
        self.assertEqual(research.lookup(lead)[0], 'ok')
        self.assertEqual(get.call_args.kwargs['params']['q'], 'manchesterdentalpractice.co.uk')


@override_settings(**SETTINGS)
class FreshnessTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='u', password='pw')
        self.lead = make_lead(self.user)

    @patch('outreach.research.requests.get', return_value=serp(place=PLACE))
    def test_cached_until_stale_then_refreshed(self, get):
        first = research.get_research(self.lead)
        self.assertEqual(first.status, 'ok')
        research.get_research(self.lead)
        self.assertEqual(get.call_count, 1)  # fresh: no second paid lookup
        LeadResearch.objects.update(checked_at=timezone.now() - timedelta(days=4))
        get.return_value = serp(place=dict(PLACE, rating=4.8))
        self.assertEqual(research.get_research(self.lead).data['rating'], 4.8)  # new details picked up
        self.assertEqual(get.call_count, 2)
        research.get_research(self.lead, force=True)
        self.assertEqual(get.call_count, 3)

    @patch('outreach.research.requests.get')
    def test_failed_refresh_keeps_good_facts(self, get):
        get.return_value = serp(place=PLACE)
        research.get_research(self.lead)
        LeadResearch.objects.update(checked_at=timezone.now() - timedelta(days=9))
        get.side_effect = requests.ConnectionError('down')
        kept = research.get_research(self.lead)
        self.assertEqual((kept.status, kept.data['name']), ('ok', 'Manchester Dental Practice'))
        self.assertIn('failed', kept.note)

    @patch('outreach.research.requests.get', return_value=serp(place=PLACE))
    def test_daily_cap_protects_credits(self, get):
        research.get_research(self.lead)
        LeadResearch.objects.update(checked_at=timezone.now() - timedelta(minutes=1))
        with override_settings(OUTREACH_RESEARCH_MAX_AGE_DAYS=0, OUTREACH_RESEARCH_DAILY_MAX=1):
            research.get_research(self.lead)
        self.assertEqual(get.call_count, 1)

    @patch('outreach.research.requests.get')
    def test_disabled(self, get):
        with override_settings(OUTREACH_RESEARCH_ENABLED=False):
            self.assertIsNone(research.get_research(self.lead))
            self.assertEqual(research.send_blocker(Mock(lead_id=1)), '')
        get.assert_not_called()

    def test_summary_lines(self):
        self.assertEqual(research.summary_line(None), 'No SerpAPI details yet.')
        ok = LeadResearch(status='ok', data={'name': 'ABC', 'rating': 4.5, 'reviews': 10, 'has_website': False,
                                              'website_changed': True})
        line = research.summary_line(ok)
        self.assertIn('4.5 stars (10 reviews)', line)
        self.assertIn('no website listed', line)
        self.assertIn('differs', line)
        bad = LeadResearch(status='no_match', note='No result matched.')
        self.assertIn('No confident match', research.summary_line(bad))


@override_settings(**SETTINGS)
class SendGateTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='u', password='pw')
        self.lead = make_lead(self.user)

    def queued(self, **kwargs):
        return OutreachMessage.objects.create(
            owner=self.user, lead=self.lead, to_email=self.lead.email, status='queued',
            subject='Website help for your practice', body=GOOD_BODY,
            approved_at=WORK_TIME - timedelta(minutes=5), **kwargs)

    @patch('outreach.mailer.send_message', return_value=('gid', 'tid'))
    @patch('outreach.research.requests.get')
    def test_closed_business_is_skipped_even_if_you_approved(self, get, send):
        get.return_value = serp(place=dict(PLACE, open_state='Permanently closed'))
        message = self.queued()
        self.assertEqual(process_queue(WORK_TIME), 'skipped')
        message.refresh_from_db()
        self.assertEqual(message.status, 'skipped')
        self.assertIn('permanently closed', message.skip_reason)
        send.assert_not_called()

    @patch('outreach.mailer.send_message', return_value=('gid', 'tid'))
    @patch('outreach.research.requests.get', return_value=serp(place=PLACE))
    def test_open_business_is_sent(self, _get, send):
        self.queued()
        self.assertEqual(process_queue(WORK_TIME), 'sent')
        send.assert_called_once()

    @patch('outreach.mailer.send_message', return_value=('gid', 'tid'))
    @patch('outreach.research.requests.get', side_effect=requests.ConnectionError('down'))
    def test_lookup_failure_blocks_auto_sent_but_not_human_approved(self, _get, send):
        auto = self.queued(auto_approved=True)
        self.assertEqual(process_queue(WORK_TIME), 'skipped')
        auto.refresh_from_db()
        self.assertIn('could not be confirmed', auto.skip_reason)
        send.assert_not_called()

        human = OutreachMessage.objects.create(
            owner=self.user, lead=make_lead(self.user, email='info@other.co.uk', link='', problem_statement=''),
            to_email='info@other.co.uk', status='queued', subject='Website help for your practice',
            body=GOOD_BODY, approved_at=WORK_TIME)
        self.assertEqual(process_queue(WORK_TIME), 'sent')
        human.refresh_from_db()
        self.assertEqual(human.status, 'sent')

    def test_message_without_lead_has_no_blocker(self):
        message = OutreachMessage.objects.create(owner=self.user, to_email='a@b.co.uk', subject='s', body='b')
        self.assertEqual(research.send_blocker(message), '')

    @patch('outreach.research.get_research', return_value=None)
    def test_no_research_object(self, _get):
        message = self.queued(auto_approved=True)
        self.assertIn('could not be checked', research.send_blocker(message))
        message.auto_approved = False
        self.assertEqual(research.send_blocker(message), '')


@override_settings(**SETTINGS)
class UsageTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='u', password='pw')
        self.lead = make_lead(self.user)

    @patch('outreach.ai.gemini.generate', return_value={'subject': 'Website help for your practice',
                                                         'body': 'Hi Manchester Dental Practice team,\n\nShort note.\n\nRegards,\nZubair'})
    @patch('outreach.research.requests.get', return_value=serp(place=PLACE))
    def test_writer_gets_real_facts_and_greeting(self, _get, generate):
        subject, body = ai.write_draft_text(self.lead)
        prompt = generate.call_args.args[0]
        self.assertIn('Business name: Manchester Dental Practice', prompt)
        self.assertIn('4.1 from 301 reviews', prompt)
        self.assertIn('already have a website', prompt)
        self.assertIn('"Hi Manchester Dental Practice team,"', prompt)
        self.assertTrue(body.startswith('Hi Manchester'))

    @patch('outreach.ai.gemini.generate')
    @patch('outreach.research.requests.get')
    def test_writer_skips_closed_and_handles_missing_facts(self, get, generate):
        get.return_value = serp(place=dict(PLACE, open_state='Permanently closed'))
        created, skipped = ai.write_drafts(self.user, [self.lead])
        self.assertEqual(created, [])
        self.assertIn('closed', skipped[0]['reason'])
        generate.assert_not_called()

        LeadResearch.objects.all().delete()
        get.return_value = serp()  # no match
        generate.return_value = {'subject': 'Website help for your practice', 'body': GOOD_BODY}
        self.assertEqual(len(ai.write_drafts(self.user, [self.lead])[0]), 1)
        self.assertIn('Start with "Hi,"', generate.call_args.args[0])
        with_site = LeadResearch.objects.get()
        with_site.status, with_site.data = 'ok', {'name': 'X', 'has_website': False}
        with_site.save()
        ai.write_draft_text(self.lead)
        self.assertIn('no website listed', generate.call_args.args[0])

    @patch('outreach.ai.gemini.generate', return_value={'verdict': 'approve', 'confidence': 1, 'issues': []})
    @patch('outreach.research.requests.get')
    def test_auto_policy_needs_a_confirmed_match(self, get, _gen):
        message = OutreachMessage.objects.create(
            owner=self.user, lead=self.lead, to_email=self.lead.email,
            subject='Website help for your practice', body=GOOD_BODY)
        get.return_value = serp(place=PLACE)
        self.assertEqual(batches.unsure_reason(message), '')
        LeadResearch.objects.all().delete()
        get.return_value = serp()
        self.assertIn('could not be confirmed', batches.unsure_reason(message))
        LeadResearch.objects.all().delete()
        get.return_value = serp(place=dict(PLACE, open_state='Permanently closed'))
        self.assertIn('could not be confirmed', batches.unsure_reason(message))

    @patch('outreach.mailer.send_message', return_value=('n', 't'))
    @patch('outreach.research.requests.get', return_value=serp(place=PLACE))
    def test_review_email_shows_serpapi_details(self, _get, send):
        message = OutreachMessage.objects.create(
            owner=self.user, lead=self.lead, to_email=self.lead.email,
            subject='Website help for your practice', body=GOOD_BODY)
        research.get_research(self.lead)
        batches.create_batch(self.user)
        self.assertIn('SerpAPI: Manchester Dental Practice, 4.1 stars (301 reviews), has a website',
                      send.call_args.args[2])
        self.assertTrue(OutreachMessage.objects.get(pk=message.pk).batch_id)

    @patch('outreach.mailer.send_message', return_value=('n', 't'))
    @patch('outreach.ai.gemini.generate', return_value={'verdict': 'approve', 'confidence': 1, 'issues': []})
    @patch('outreach.research.requests.get', return_value=serp(place=PLACE))
    def test_auto_approved_flag_is_recorded(self, _get, _gen, _send):
        OutreachMessage.objects.create(
            owner=self.user, lead=self.lead, to_email=self.lead.email,
            subject='Website help for your practice', body=GOOD_BODY)
        with override_settings(OUTREACH_AUTO_SEND_ENABLED=True):
            batch = batches.create_batch(self.user)
            batches.auto_approve_batch(batch.pk)
        self.assertTrue(OutreachMessage.objects.get().auto_approved)
