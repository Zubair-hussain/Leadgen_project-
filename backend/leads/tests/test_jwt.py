"""Tests for the Django SimpleJWT authentication integration."""
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, APITestCase

from leads.authentication import FallthroughJWTAuthentication
from leads.models import Lead


class JwtAuthFlowTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="jwtuser", password="s3cret-pw", email="jwt@example.com"
        )

    def obtain(self, username="jwtuser", password="s3cret-pw"):
        return self.client.post(
            "/api/token/", {"username": username, "password": password}, format="json"
        )

    def test_obtain_token_pair(self):
        response = self.obtain()
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_obtain_rejects_bad_credentials(self):
        response = self.obtain(password="wrong")
        self.assertEqual(response.status_code, 401)

    def test_access_token_authenticates_protected_endpoint(self):
        access = self.obtain().data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        response = self.client.get("/api/leads/")

        self.assertEqual(response.status_code, 200)

    def test_access_token_scopes_to_the_owner(self):
        other = get_user_model().objects.create_user(username="other", password="pw")
        Lead.objects.create(owner=self.user, email="mine@example.com", source="reddit")
        Lead.objects.create(owner=other, email="theirs@example.com", source="reddit")
        access = self.obtain().data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        response = self.client.get("/api/leads/")

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["email"], "mine@example.com")

    def test_refresh_returns_new_access_token(self):
        refresh = self.obtain().data["refresh"]

        response = self.client.post(
            "/api/token/refresh/", {"refresh": refresh}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

    def test_verify_accepts_a_valid_token(self):
        access = self.obtain().data["access"]

        response = self.client.post(
            "/api/token/verify/", {"token": access}, format="json"
        )

        self.assertEqual(response.status_code, 200)

    def test_verify_rejects_garbage(self):
        response = self.client.post(
            "/api/token/verify/", {"token": "not-a-token"}, format="json"
        )

        self.assertEqual(response.status_code, 401)

    def test_invalid_bearer_token_is_unauthorized(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer garbage.token.value")

        response = self.client.get("/api/leads/")

        self.assertEqual(response.status_code, 401)


class FallthroughJWTAuthenticationTests(APITestCase):
    def test_no_header_returns_none(self):
        request = APIRequestFactory().get("/")
        self.assertIsNone(FallthroughJWTAuthentication().authenticate(request))

    def test_non_jwt_bearer_falls_through(self):
        # A Firebase-style opaque token is not a valid SimpleJWT: defer, don't raise.
        request = APIRequestFactory().get(
            "/", HTTP_AUTHORIZATION="Bearer firebase-id-token"
        )
        self.assertIsNone(FallthroughJWTAuthentication().authenticate(request))


class FirebaseTokenExchangeTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="fbuser", password="pw", email="fb@example.com"
        )

    def test_exchange_mints_a_django_jwt_pair_for_the_user(self):
        # The Firebase ID token is verified by the auth chain (covered in
        # test_authentication.py); here we assert the view mints a usable pair.
        self.client.force_authenticate(user=self.user)

        response = self.client.post("/api/token/firebase/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["email"], "fb@example.com")

    def test_exchanged_access_token_authenticates_api_calls(self):
        self.client.force_authenticate(user=self.user)
        access = self.client.post("/api/token/firebase/").data["access"]

        # Drop the forced session auth and rely solely on the minted JWT.
        self.client.force_authenticate(user=None)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = self.client.get("/api/leads/")

        self.assertEqual(response.status_code, 200)

    def test_exchange_requires_authentication(self):
        response = self.client.post("/api/token/firebase/")
        self.assertEqual(response.status_code, 401)
