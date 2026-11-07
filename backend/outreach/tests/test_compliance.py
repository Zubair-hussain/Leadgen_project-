from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from leads import directories
from leads.models import Lead
from leads.regions import detect_country, region_of
from outreach import branding, compliance, playbook
from outreach.models import OutreachMessage
from outreach.services import in_send_window, process_queue

STRICT = dict(OUTREACH_REQUIRE_REGION=True, OUTREACH_DRY_RUN=False, OUTREACH_SENDER_ADDRESS='1 Test St, London')


def make_message(email, location='', **lead_fields):
    user = get_user_model().objects.get_or_create(username='u')[0]
    lead = Lead.objects.create(owner=user, email=email, source=lead_fields.pop('source', 'yelp'),
                               location=location, is_verified=True, **lead_fields)
    return OutreachMessage.objects.create(owner=user, lead=lead, to_email=email, subject='x', body='Hi')


class RegionTests(SimpleTestCase):
    def test_detects_country(self):
        self.assertEqual(detect_country(location='12 Pitt St, Sydney NSW 2000'), 'AU')
        self.assertEqual(detect_country(location='Austin, TX 78701'), 'US')
        self.assertEqual(detect_country(location='Leeds, United Kingdom'), 'GB')
        self.assertEqual(detect_country(phone='+49 30 123456'), 'DE')
        self.assertEqual(detect_country(link='https://bakery.com.au'), 'AU')
        self.assertEqual(detect_country(location='Somewhere'), '')

    def test_regions(self):
        self.assertEqual([region_of(c) for c in ('US', 'GB', 'AU', 'FR', 'BR')], ['US', 'UK', 'AU', 'EU', ''])


@override_settings(**STRICT)
class ComplianceTests(TestCase):
    def test_unknown_country_is_blocked(self):
        self.assertIn('unknown', compliance.problems(make_message('a@shop.com', 'Somewhere')))

    def test_germany_needs_consent(self):
        self.assertIn('prior consent', compliance.problems(make_message('a@shop.de', 'Berlin, Germany')))

    def test_personal_mailbox_blocked_in_eu_uk_au_but_not_us(self):
        self.assertIn('Personal mailboxes', compliance.problems(make_message('a@gmail.com', 'Leeds, UK')))
        self.assertEqual(compliance.problems(make_message('b@gmail.com', 'Austin, TX 78701')), '')

    def test_business_address_ok_and_needs_postal_address(self):
        message = make_message('a@shop.com.au', 'Sydney NSW 2000')
        self.assertEqual(compliance.problems(message), '')
        with override_settings(OUTREACH_SENDER_ADDRESS=''):
            self.assertIn('OUTREACH_SENDER_ADDRESS', compliance.problems(message))

    def test_footer_depends_on_region(self):
        us = '\n'.join(compliance.footer_lines('US', 'yelp'))
        uk = '\n'.join(compliance.footer_lines('UK', 'nextdoor'))
        au = '\n'.join(compliance.footer_lines('AU', 'truelocal'))
        self.assertIn('1 Test St', us)
        self.assertNotIn('legitimate interest', us)
        self.assertIn('legitimate interest', uk)
        self.assertIn('Nextdoor', uk)
        self.assertIn('True Local', au)

    def test_compose_includes_footer_in_text_and_html(self):
        text, html = branding.compose('s', 'Hello there.', region='UK', source='yelp')
        self.assertIn('Sent by Zubair Hussain', text)
        self.assertIn('legitimate interest', html)

    @override_settings(OUTREACH_COMPLIANCE_ENABLED=False)
    def test_can_be_switched_off(self):
        self.assertEqual(compliance.problems(make_message('a@gmail.com', 'Leeds, UK')), '')


class DailyAndWindowTests(TestCase):
    @override_settings(OUTREACH_DAILY_MIN=10, OUTREACH_DAILY_LIMIT=20, OUTREACH_WARMUP_ENABLED=False)
    def test_daily_target_is_10_to_20_and_repeatable(self):
        day = datetime(2026, 10, 13).date()
        targets = {playbook.daily_target(day + timedelta(days=i)) for i in range(60)}
        self.assertTrue(targets <= set(range(10, 21)))
        self.assertGreater(len(targets), 3)
        self.assertEqual(playbook.daily_target(day), playbook.daily_target(day))

    def test_window_follows_region(self):
        utc_evening = datetime(2026, 10, 13, 22, 0, tzinfo=dt_timezone.utc)  # Wednesday 09:00 in Sydney
        self.assertTrue(in_send_window(utc_evening, 'AU'))
        self.assertFalse(in_send_window(utc_evening, 'UK'))

    @override_settings(OUTREACH_DRY_RUN=True, OUTREACH_TRANSPORT='gmail', OUTREACH_WARMUP_ENABLED=False,
                       OUTREACH_REQUIRE_REGION=True)
    def test_queue_sends_australian_lead_in_australian_hours(self):
        message = make_message('a@shop.com.au', 'Sydney NSW 2000')
        message.status = OutreachMessage.Status.QUEUED
        message.approved_at = timezone.now()
        message.save()
        with patch('outreach.research.send_blocker', return_value=''):
            self.assertEqual(process_queue(datetime(2026, 10, 13, 22, 0, tzinfo=dt_timezone.utc)), 'sent')


class DirectoryTests(SimpleTestCase):
    def test_clean_name(self):
        self.assertEqual(directories.clean_name("Joe's Plumbing - Austin, TX | Nextdoor"), "Joe's Plumbing")
        self.assertEqual(directories.clean_name('1. Best Cafe - Yelp'), 'Best Cafe')

    @override_settings(YELP_API_KEY='k')
    @patch('leads.directories.requests.get')
    def test_yelp_api_then_website_email(self, get):
        get.return_value = MagicMock(json=lambda: {'businesses': [{'name': 'Acme Plumbing', 'phone': '+15125550100',
                                                                   'location': {'display_address': ['1 Main', 'Austin, TX']},
                                                                   'url': 'https://yelp.com/biz/acme'}]},
                                     raise_for_status=lambda: None)
        client = MagicMock()
        client.search.return_value = {'place_results': {'title': 'Acme Plumbing', 'website': 'https://acme.com',
                                                        'address': 'Austin, TX', 'phone': '+15125550100'}}
        generator = MagicMock(serpapi_key='s')
        generator._extract_active_email_from_website.return_value = 'info@acme.com'
        with patch('serpapi.Client', return_value=client):
            leads = directories.discover(generator, 'yelp', 'plumber', 'Austin, TX')
        self.assertEqual(leads[0]['email'], 'info@acme.com')
        self.assertEqual(leads[0]['source'], 'yelp')
        self.assertIn('Local business: Acme Plumbing.', leads[0]['problem_statement'])

    @patch('leads.directories.requests.get')
    def test_nextdoor_uses_search_results_never_the_site(self, get):
        client = MagicMock()
        client.search.side_effect = [
            {'organic_results': [{'title': 'Bondi Bakes - Bondi | Nextdoor', 'link': 'https://nextdoor.com/pages/x'}]},
            {'place_results': {'title': 'Bondi Bakes', 'website': 'https://bondibakes.com.au', 'address': 'Bondi NSW'}},
        ]
        generator = MagicMock(serpapi_key='s')
        generator._extract_active_email_from_website.return_value = 'hello@bondibakes.com.au'
        with patch('serpapi.Client', return_value=client):
            leads = directories.discover(generator, 'nextdoor', 'bakery', 'Bondi NSW')
        self.assertEqual(leads[0]['email'], 'hello@bondibakes.com.au')
        get.assert_not_called()

    def test_unknown_source_or_no_location(self):
        self.assertEqual(directories.discover(MagicMock(), 'facebook', 'x', 'y'), [])
        self.assertEqual(directories.discover(MagicMock(), 'yelp', 'x', ''), [])
