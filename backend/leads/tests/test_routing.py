import importlib
import os
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase


class RootAndAdminUrlTests(TestCase):
    def test_root_and_health_respond(self):
        self.assertEqual(self.client.get('/').status_code, 200)
        self.assertEqual(self.client.get('/api/health/').status_code, 200)


class AdminUrlSettingTests(SimpleTestCase):
    def _admin_url(self, value):
        env = {} if value is None else {'ADMIN_URL': value}
        with patch.dict(os.environ, env, clear=False):
            if value is None:
                os.environ.pop('ADMIN_URL', None)
            from leadgen import settings
            result = importlib.reload(settings).ADMIN_URL
        importlib.reload(settings)
        return result

    def test_blank_missing_and_messy_values_are_safe(self):
        self.assertEqual(self._admin_url(''), 'admin/')
        self.assertEqual(self._admin_url(None), 'admin/')
        self.assertEqual(self._admin_url('/'), 'admin/')
        self.assertEqual(self._admin_url('secret-path'), 'secret-path/')
        self.assertEqual(self._admin_url('/secret-path/'), 'secret-path/')
