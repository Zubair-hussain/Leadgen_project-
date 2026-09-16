from unittest.mock import patch

from django.test import TestCase
from rest_framework import exceptions
from rest_framework.test import APIRequestFactory

from leads.authentication import FirebaseAuthentication


class FirebaseAuthenticationTests(TestCase):
    @patch("leads.authentication._firebase_app")
    @patch("firebase_admin.auth.verify_id_token")
    def test_valid_firebase_token_creates_user(self, mock_verify, _mock_app):
        mock_verify.return_value = {"uid": "abc123", "email": "person@example.com"}
        request = APIRequestFactory().get("/", HTTP_AUTHORIZATION="Bearer token")

        user, decoded = FirebaseAuthentication().authenticate(request)

        self.assertEqual(user.email, "person@example.com")
        self.assertEqual(decoded["uid"], "abc123")

    def test_missing_header_returns_none(self):
        request = APIRequestFactory().get("/")

        self.assertIsNone(FirebaseAuthentication().authenticate(request))

    def test_malformed_header_fails(self):
        request = APIRequestFactory().get("/", HTTP_AUTHORIZATION="Token nope")

        with self.assertRaises(exceptions.AuthenticationFailed):
            FirebaseAuthentication().authenticate(request)
