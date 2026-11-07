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

CELERY_TASK_ALWAYS_EAGER = True
OUTREACH_BATCH_QUIET_SECONDS = 120

# Tests must never call real paid APIs, even if backend/.env holds real keys.
SERPAPI_KEY = ''
GEMINI_API_KEY = ''

# Tests must never touch a real mailbox either. Older tests configure the Gmail client;
# SMTP/IMAP tests opt in with override_settings and mock smtplib/imaplib.
OUTREACH_TRANSPORT = 'gmail'
OUTREACH_SMTP_PASSWORD = ''
OUTREACH_IMAP_PASSWORD = ''
OUTREACH_PORTFOLIO_URL = ''
OUTREACH_WARMUP_ENABLED = False

# Older tests use leads without a known country; compliance tests opt in with override_settings.
OUTREACH_REQUIRE_REGION = False
OUTREACH_DAILY_MIN = 10
OUTREACH_DAILY_LIMIT = 10
OUTREACH_SENDER_ADDRESS = '1 Test Street, London'
YELP_API_KEY = ''
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}
