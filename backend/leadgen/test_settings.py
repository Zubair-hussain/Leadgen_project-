import os

os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("SECRET_KEY", "test-secret")

from .settings import *  # noqa: F401,F403

DEBUG = True
SECRET_KEY = "test-secret"
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
LEADGEN_SYNC_REQUESTS = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] = [
    "leads.authentication.FallthroughJWTAuthentication",
    "rest_framework.authentication.SessionAuthentication",
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
