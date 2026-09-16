from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from leads.models import Lead


class LeadApiTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="owner", password="pw")
        self.other = User.objects.create_user(username="other", password="pw")

    def auth(self, user=None):
        self.client.force_authenticate(user=user or self.user)

    def test_health_is_public_and_minimal(self):
        response = self.client.get("/api/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "healthy")
        self.assertNotIn("sender", response.data)
        self.assertNotIn("serpapi_ready", response.data)

    def test_lead_list_requires_authentication(self):
        response = self.client.get("/api/leads/")

        # JWT auth advertises a WWW-Authenticate challenge, so DRF returns 401.
        self.assertEqual(response.status_code, 401)

    def test_lead_list_is_scoped_to_current_user(self):
        Lead.objects.create(owner=self.user, email="a@example.com", source="reddit")
        Lead.objects.create(owner=self.other, email="b@example.com", source="reddit")
        self.auth()

        response = self.client.get("/api/leads/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["email"], "a@example.com")

    def test_delete_only_deletes_owned_lead(self):
        lead = Lead.objects.create(owner=self.other, email="other@example.com", source="reddit")
        self.auth()

        response = self.client.delete(f"/api/leads/{lead.id}/")

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Lead.objects.filter(id=lead.id).exists())

    @patch("leads.views.EmailVerifier.is_valid_email", return_value=True)
    def test_bulk_verify_updates_owned_unverified_leads(self, _mock_verify):
        lead = Lead.objects.create(owner=self.user, email="bulk@example.com", source="reddit")
        Lead.objects.create(owner=self.other, email="otherbulk@example.com", source="reddit")
        self.auth()

        response = self.client.post("/api/leads/bulk-verify/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["processed"], 1)
        lead.refresh_from_db()
        self.assertTrue(lead.is_verified)

    def test_export_streams_only_verified_owned_leads(self):
        Lead.objects.create(
            owner=self.user,
            email="owned@example.com",
            source="reddit",
            is_verified=True,
        )
        Lead.objects.create(
            owner=self.other,
            email="other@example.com",
            source="reddit",
            is_verified=True,
        )
        self.auth()

        response = self.client.get("/api/leads/export/")
        content = b"".join(response.streaming_content).decode("utf-8")

        self.assertEqual(response.status_code, 200)
        self.assertIn("owned@example.com", content)
        self.assertNotIn("other@example.com", content)

    @override_settings(MAX_VERIFY_UPLOAD_BYTES=4)
    def test_file_verify_rejects_large_uploads(self):
        self.auth()
        upload = BytesIO(b"email@example.com")
        upload.name = "emails.txt"

        response = self.client.post("/api/leads/verify-file/", {"file": upload})

        self.assertEqual(response.status_code, 413)

    @patch("leads.views.EmailVerifier.is_valid_email", return_value=True)
    def test_file_verify_extracts_emails(self, _mock_verify):
        self.auth()
        upload = BytesIO(b"email@example.com")
        upload.name = "emails.txt"

        response = self.client.post("/api/leads/verify-file/", {"file": upload})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["processed"], 1)

    @patch("leads.views.EmailVerifier.is_valid_email", return_value=True)
    def test_single_verify_uses_backend_verifier(self, mock_verify):
        self.auth()

        response = self.client.post("/api/leads/verify-single/", {"email": "email@example.com"})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_verified"])
        mock_verify.assert_called_once_with("email@example.com")

    @patch("leads.views.EmailVerifier.is_valid_email", side_effect=[True, False])
    def test_multi_verify_limits_to_submitted_emails(self, _mock_verify):
        self.auth()

        response = self.client.post(
            "/api/leads/verify-multi/",
            {"emails": ["a@example.com", "b@example.com"]},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertTrue(response.data["results"][0]["is_verified"])
        self.assertFalse(response.data["results"][1]["is_verified"])

    def test_generate_requires_category(self):
        self.auth()

        response = self.client.post("/api/generate/", {"platforms": ["reddit"]}, format="json")

        self.assertEqual(response.status_code, 400)

    def test_generate_requires_platforms(self):
        self.auth()

        response = self.client.post(
            "/api/generate/",
            {"category": "dentists", "platforms": []},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    @patch("leads.views.LeadGenerator.generate_leads", return_value=[])
    def test_generate_leads_calls_service_with_owner(self, mock_generate):
        self.auth()

        response = self.client.post("/api/generate/", {
            "category": "dentists",
            "platforms": ["reddit"],
            "target_location": "Austin",
        }, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["leads"], [])
        self.assertEqual(mock_generate.call_args.kwargs["owner"], self.user)

    @override_settings(LEADGEN_SYNC_REQUESTS=False)
    @patch("leads.views.generate_leads_task.delay")
    def test_generate_can_queue_celery_task(self, mock_delay):
        mock_delay.return_value.id = "task-123"
        self.auth()

        response = self.client.post("/api/generate/", {
            "category": "dentists",
            "platforms": ["reddit"],
            "target_location": "Austin",
        }, format="json")

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["task_id"], "task-123")

    def test_deliverability_check_returns_result(self):
        self.auth()

        with patch("leads.views.DeliverabilityPolicyChecker.check", return_value={"score": 100}):
            response = self.client.post(
                "/api/deliverability/check/",
                {"sender_email": "sales@validdomain.io"},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["score"], 100)
