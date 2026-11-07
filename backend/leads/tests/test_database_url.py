import importlib
import os
from unittest.mock import patch

from django.test import SimpleTestCase


class DatabaseUrlTests(SimpleTestCase):
    def test_ssl_options_survive_parsing(self):
        url = 'postgresql://user:p%40ss@ep-x-pooler.neon.tech/neondb?sslmode=require&channel_binding=require&junk=1'
        with patch.dict(os.environ, {'DATABASE_URL': url}):
            from leadgen import settings
            settings = importlib.reload(settings)
            db = settings.DATABASES['default']
        self.assertEqual((db['HOST'], db['NAME'], db['USER'], db['PASSWORD']), ('ep-x-pooler.neon.tech', 'neondb', 'user', 'p@ss'))
        self.assertEqual(db['OPTIONS']['sslmode'], 'require')
        self.assertEqual(db['OPTIONS']['channel_binding'], 'require')
        self.assertNotIn('junk', db['OPTIONS'])
        importlib.reload(settings)
