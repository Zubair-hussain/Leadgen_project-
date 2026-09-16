"""Premium (admin/staff) accounts bypass the lead-generation rate limit."""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APITestCase


class PremiumRateLimitTests(APITestCase):
    def setUp(self):
        cache.clear()  # isolate the per-IP rate-limit counter
        User = get_user_model()
        self.user = User.objects.create_user(username="basic", password="pw")
        self.admin = User.objects.create_user(username="boss", password="pw", is_staff=True)

    def tearDown(self):
        cache.clear()

    def _generate(self):
        return self.client.post(
            "/api/generate/",
            {"category": "Dentists", "platforms": ["reddit"], "target_location": "Austin"},
            format="json",
        )

    @patch("leads.views.LeadGenerator.generate_leads", return_value=[])
    def test_basic_user_is_rate_limited(self, _mock):
        self.client.force_authenticate(user=self.user)
        statuses = [self._generate().status_code for _ in range(6)]
        # 5/5m allowed → the 6th request is throttled.
        self.assertEqual(statuses[-1], 429)

    @patch("leads.views.LeadGenerator.generate_leads", return_value=[])
    def test_staff_user_bypasses_the_limit(self, _mock):
        self.client.force_authenticate(user=self.admin)
        statuses = [self._generate().status_code for _ in range(7)]
        # premium/admin: never throttled.
        self.assertNotIn(429, statuses)
        self.assertTrue(all(s == 200 for s in statuses))
