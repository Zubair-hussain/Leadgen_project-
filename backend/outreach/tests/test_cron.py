from unittest.mock import patch

from django.test import TestCase, override_settings


@override_settings(CRON_SECRET='s3cret')
class CronTickTests(TestCase):
    url = '/api/outreach/cron/tick/'

    def test_rejects_missing_or_wrong_secret(self):
        self.assertEqual(self.client.post(self.url).status_code, 401)
        self.assertEqual(self.client.post(self.url, HTTP_AUTHORIZATION='Bearer nope').status_code, 401)

    @override_settings(CRON_SECRET='')
    def test_unconfigured_secret_is_refused(self):
        self.assertEqual(self.client.post(self.url, HTTP_AUTHORIZATION='Bearer ').status_code, 503)

    @patch('outreach.cron.weekly_report', return_value='not-due')
    @patch('outreach.cron.schedule_followups', return_value='followups-ok')
    @patch('outreach.cron.process_batches', return_value='batches-ok')
    @patch('outreach.cron.process_queue', return_value='queue-empty')
    def test_runs_all_jobs(self, *_):
        response = self.client.post(self.url, HTTP_AUTHORIZATION='Bearer s3cret')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'queue': 'queue-empty', 'batches': 'batches-ok',
                                           'followups': 'followups-ok', 'report': 'not-due'})

    @patch('outreach.cron.run_autopilot', return_value='drafted 2, skipped 0')
    def test_autopilot_endpoint(self, *_):
        url = '/api/outreach/cron/autopilot/'
        self.assertEqual(self.client.post(url).status_code, 401)
        data = self.client.post(url, HTTP_AUTHORIZATION='Bearer s3cret').json()
        self.assertEqual(data, {'autopilot': 'drafted 2, skipped 0'})

    @patch('outreach.cron.weekly_report', return_value='not-due')
    @patch('outreach.cron.schedule_followups', return_value='ok')
    @patch('outreach.cron.process_batches', side_effect=RuntimeError('boom'))
    @patch('outreach.cron.process_queue', return_value='sent')
    def test_one_failure_does_not_stop_the_rest(self, *_):
        data = self.client.get(self.url, HTTP_AUTHORIZATION='Bearer s3cret').json()
        self.assertEqual((data['queue'], data['batches'], data['followups']), ('sent', 'error', 'ok'))
