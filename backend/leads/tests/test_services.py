from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from leads.models import Lead
from leads.services import DeliverabilityPolicyChecker, EmailVerifier, LeadGenerator


class EmailVerifierTests(TestCase):
    def test_normalize_email_strips_mailto_and_query(self):
        self.assertEqual(
            EmailVerifier.normalize_email("mailto:USER@Example.com?subject=hi"),
            "user@example.com",
        )

    def test_invalid_system_addresses_are_rejected(self):
        self.assertFalse(EmailVerifier.is_valid_syntax("noreply@example.com"))
        self.assertFalse(EmailVerifier.is_valid_syntax("person@test.com"))


class DeliverabilityPolicyCheckerTests(TestCase):
    @patch.object(DeliverabilityPolicyChecker, "_check_dkim", return_value=(["google"], ["google"]))
    @patch.object(DeliverabilityPolicyChecker, "_mx_records", return_value=["mx.example.com"])
    @patch.object(DeliverabilityPolicyChecker, "_txt_records")
    def test_policy_check_scores_authenticated_sender(self, mock_txt, _mock_mx, _mock_dkim):
        def records(name):
            if name == "validdomain.io":
                return ["v=spf1 include:_spf.google.com ~all"]
            if name == "_dmarc.validdomain.io":
                return ["v=DMARC1; p=none"]
            return []

        mock_txt.side_effect = records

        result = DeliverabilityPolicyChecker.check(
            sender_email="sales@validdomain.io",
            body="This is a normal plain text body with enough detail for a real first message.",
            include_unsubscribe=True,
            smtp_host="smtp.gmail.com",
        )

        self.assertGreaterEqual(result["score"], 80)
        self.assertEqual(result["domain"], "validdomain.io")


class LeadGeneratorTests(TestCase):
    def setUp(self):
        self.generator = LeadGenerator()

    @patch("leads.services.socket.getaddrinfo")
    def test_private_urls_are_blocked(self, mock_addrinfo):
        mock_addrinfo.return_value = [(None, None, None, None, ("127.0.0.1", 0))]

        self.assertFalse(self.generator._is_safe_public_url("http://localhost/admin"))
        self.assertFalse(self.generator._is_safe_public_url("http://example.com/admin"))

    @patch("leads.services.socket.getaddrinfo")
    @patch("leads.services.requests.get")
    def test_fetch_page_blocks_private_targets(self, mock_get, mock_addrinfo):
        mock_addrinfo.return_value = [(None, None, None, None, ("10.0.0.1", 0))]

        html = self.generator._fetch_page("http://example.com")

        self.assertEqual(html, "")
        mock_get.assert_not_called()

    @patch.object(EmailVerifier, "is_valid_email", return_value=True)
    def test_save_leads_sets_owner_and_deduplicates(self, _mock_valid):
        User = get_user_model()
        owner = User.objects.create_user(username="owner")
        leads = [
            {
                "email": "a@example.com",
                "phone": "",
                "source": "reddit",
                "location": "Remote",
                "link": "https://example.com",
                "problem_statement": "Needs help",
            },
            {
                "email": "a@example.com",
                "phone": "",
                "source": "reddit",
                "location": "Remote",
                "link": "https://example.com",
                "problem_statement": "Duplicate",
            },
        ]

        saved = self.generator._save_leads(leads, "marketing", owner=owner)

        self.assertEqual(len(saved), 1)
        self.assertEqual(Lead.objects.get().owner, owner)
