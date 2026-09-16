from functools import lru_cache

from django.contrib.auth import get_user_model
from django.utils.text import slugify
from rest_framework import authentication, exceptions
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class FallthroughJWTAuthentication(JWTAuthentication):
    """Validate Django SimpleJWT access tokens, but defer instead of failing.

    Both this class and :class:`FirebaseAuthentication` use the ``Bearer``
    scheme. DRF stops walking the authenticator chain as soon as one raises
    ``AuthenticationFailed``. Returning ``None`` for a token that is not a
    valid SimpleJWT lets a Firebase ID token fall through to Firebase auth,
    so the two schemes can coexist on the same header.
    """

    def authenticate(self, request):
        header = self.get_header(request)
        if header is None:
            return None
        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None
        try:
            validated_token = self.get_validated_token(raw_token)
        except (InvalidToken, TokenError):
            # Not a Django-issued JWT — let the next authenticator try.
            return None
        return self.get_user(validated_token), validated_token


@lru_cache(maxsize=1)
def _firebase_app():
    try:
        import firebase_admin
        from firebase_admin import credentials
    except ImportError as exc:
        raise exceptions.AuthenticationFailed(
            "Firebase authentication dependency is not installed."
        ) from exc

    if firebase_admin._apps:
        return firebase_admin.get_app()
    return firebase_admin.initialize_app(credentials.ApplicationDefault())


class FirebaseAuthentication(authentication.BaseAuthentication):
    """Authenticate API requests with a Firebase ID token."""

    keyword = "Bearer"

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).decode("utf-8")
        if not header:
            return None

        parts = header.split()
        if len(parts) != 2 or parts[0] != self.keyword:
            raise exceptions.AuthenticationFailed("Use Authorization: Bearer <firebase_id_token>.")

        try:
            from firebase_admin import auth as firebase_auth
            decoded = firebase_auth.verify_id_token(parts[1], app=_firebase_app())
        except Exception as exc:
            raise exceptions.AuthenticationFailed("Invalid Firebase ID token.") from exc

        email = decoded.get("email")
        uid = decoded.get("uid") or decoded.get("sub")
        if not uid:
            raise exceptions.AuthenticationFailed("Firebase token is missing a user id.")

        User = get_user_model()
        username = slugify(email or uid)[:140] or uid[:140]
        user, _created = User.objects.get_or_create(
            username=username,
            defaults={"email": email or ""},
        )
        if email and user.email != email:
            user.email = email
            user.save(update_fields=["email"])
        return user, decoded
