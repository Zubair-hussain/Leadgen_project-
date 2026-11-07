import os
from pathlib import Path
from dotenv import load_dotenv
from .env import env_bool, env_list, required_env

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = env_bool('DEBUG', False)

SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'dev-only-insecure-secret-key'
    else:
        SECRET_KEY = required_env('SECRET_KEY')

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', 'localhost,127.0.0.1')
# Render sets this to the service's public hostname.
if os.getenv('RENDER_EXTERNAL_HOSTNAME'):
    ALLOWED_HOSTS.append(os.environ['RENDER_EXTERNAL_HOSTNAME'])
# Behind an HTTPS reverse proxy (Caddy/nginx on the Oracle server): trust its X-Forwarded-Proto
# and the public origin, so review links neither redirect-loop nor fail CSRF.
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS', '')
if env_bool('USE_X_FORWARDED_PROTO', False):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_celery_beat',
    'leads.apps.LeadsConfig',
    'outreach.apps.OutreachConfig',
]

if DEBUG:
    INSTALLED_APPS.append('debug_toolbar')

CORS_ALLOWED_ORIGINS = env_list(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,'
    'http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174',
)

CORS_ALLOW_CREDENTIALS = env_bool('CORS_ALLOW_CREDENTIALS', DEBUG)

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'leadgen.security.SecurityHeadersMiddleware',
]

if DEBUG:
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')

ROOT_URLCONF = 'leadgen.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'leadgen.wsgi.application'

def _database_from_url(url):
    """Render/Heroku style DATABASE_URL -> Django settings (no extra dependency)."""
    from urllib.parse import unquote, urlparse
    parsed = urlparse(url)
    return {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': parsed.path.lstrip('/'),
        'USER': unquote(parsed.username or ''),
        'PASSWORD': unquote(parsed.password or ''),
        'HOST': parsed.hostname or '',
        'PORT': str(parsed.port or 5432),
        'CONN_MAX_AGE': 60,
        'OPTIONS': {'connect_timeout': 10},
    }


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'leadgen'),
        'USER': os.getenv('POSTGRES_USER', 'leadgen_user'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD'),
        'HOST': os.getenv('POSTGRES_HOST', 'db'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
        'OPTIONS': {
            'connect_timeout': 10,
        },
    }
}

if os.getenv('DATABASE_URL'):
    DATABASES['default'] = _database_from_url(os.environ['DATABASE_URL'])

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = os.getenv('TIME_ZONE', 'UTC')
USE_I18N = True
USE_TZ = True

# Celery Configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_BEAT_SCHEDULE = {
    'process-outreach-queue': {
        'task': 'outreach.tasks.process_outreach_queue',
        'schedule': 60.0,
    },
    'process-outreach-batches': {
        'task': 'outreach.tasks.process_batches',
        'schedule': 60.0,
    },
    # Reads the inbox for replies/bounces first, then queues follow-ups that are due.
    'process-outreach-followups': {
        'task': 'outreach.tasks.process_followups',
        'schedule': float(os.getenv('OUTREACH_INBOX_SYNC_SECONDS', '300')),
    },
}

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email sender configuration
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'noreply@example.com')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

SERPAPI_KEY = os.getenv('SERPAPI_KEY', '')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.8-flash')

# Outreach. See docs/outreach.md for setup.
# "smtp" sends from your own mailbox (Hostinger by default); "gmail" uses the Gmail API.
OUTREACH_TRANSPORT = os.getenv('OUTREACH_TRANSPORT', 'smtp').strip().lower()
OUTREACH_FROM_EMAIL = os.getenv('OUTREACH_FROM_EMAIL', 'thezubairh@gmail.com')
OUTREACH_FROM_NAME = os.getenv('OUTREACH_FROM_NAME', 'Zubair Hussain')
OUTREACH_SMTP_HOST = os.getenv('OUTREACH_SMTP_HOST', 'smtp.hostinger.com')
OUTREACH_SMTP_PORT = int(os.getenv('OUTREACH_SMTP_PORT', '465'))
OUTREACH_SMTP_SSL = env_bool('OUTREACH_SMTP_SSL', True)  # 465 = SSL; set False for 587 + STARTTLS
OUTREACH_SMTP_USER = os.getenv('OUTREACH_SMTP_USER', '') or OUTREACH_FROM_EMAIL
OUTREACH_SMTP_PASSWORD = os.getenv('OUTREACH_SMTP_PASSWORD', '')
# IMAP on the same mailbox: replies stop follow-ups, bounces/opt-outs are suppressed, sent copies saved.
OUTREACH_IMAP_HOST = os.getenv('OUTREACH_IMAP_HOST', 'imap.hostinger.com')
OUTREACH_IMAP_PORT = int(os.getenv('OUTREACH_IMAP_PORT', '993'))
OUTREACH_IMAP_USER = os.getenv('OUTREACH_IMAP_USER', '') or OUTREACH_SMTP_USER
OUTREACH_IMAP_PASSWORD = os.getenv('OUTREACH_IMAP_PASSWORD', '') or OUTREACH_SMTP_PASSWORD
OUTREACH_IMAP_SENT_FOLDER = os.getenv('OUTREACH_IMAP_SENT_FOLDER', 'INBOX.Sent')
OUTREACH_IMAP_SAVE_SENT = env_bool('OUTREACH_IMAP_SAVE_SENT', True)
OUTREACH_INBOX_SYNC_ENABLED = env_bool('OUTREACH_INBOX_SYNC_ENABLED', True)
OUTREACH_INBOX_LOOKBACK_DAYS = int(os.getenv('OUTREACH_INBOX_LOOKBACK_DAYS', '14'))
OUTREACH_INBOX_MAX_SCAN = int(os.getenv('OUTREACH_INBOX_MAX_SCAN', '500'))
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REFRESH_TOKEN = os.getenv('GOOGLE_REFRESH_TOKEN', '')
# Branded email: personal-letter body + ZH. signature card (HTML), with a plain-text twin.
OUTREACH_HTML_EMAIL = env_bool('OUTREACH_HTML_EMAIL', True)
OUTREACH_SIGNATURE = env_bool('OUTREACH_SIGNATURE', True)
OUTREACH_SENDER_TITLE = os.getenv('OUTREACH_SENDER_TITLE', 'Full Stack Developer')
# Dry run is ON unless explicitly disabled: nothing leaves the machine.
OUTREACH_DRY_RUN = env_bool('OUTREACH_DRY_RUN', True)
# Each day a random target between DAILY_MIN and DAILY_LIMIT (default 10-20) is picked; never exceeded.
OUTREACH_DAILY_MIN = int(os.getenv('OUTREACH_DAILY_MIN', '10'))
OUTREACH_DAILY_LIMIT = int(os.getenv('OUTREACH_DAILY_LIMIT', '20'))
# Regional compliance (US CAN-SPAM, UK/EU GDPR+PECR, Australia Spam Act). See outreach/compliance.py.
OUTREACH_COMPLIANCE_ENABLED = env_bool('OUTREACH_COMPLIANCE_ENABLED', True)
OUTREACH_REQUIRE_REGION = env_bool('OUTREACH_REQUIRE_REGION', True)
OUTREACH_BLOCKED_COUNTRIES = os.getenv('OUTREACH_BLOCKED_COUNTRIES', 'DE,AT')
OUTREACH_SENDER_ADDRESS = os.getenv('OUTREACH_SENDER_ADDRESS', '')  # postal address, required in every email
OUTREACH_PRIVACY_URL = os.getenv('OUTREACH_PRIVACY_URL', '')
# Directory discovery (Yelp API, Nextdoor and True Local via search results). See leads/directories.py.
YELP_API_KEY = os.getenv('YELP_API_KEY', '')
DIRECTORY_MAX_PER_RUN = int(os.getenv('DIRECTORY_MAX_PER_RUN', '15'))
# Warm-up: a new mailbox starts at WARMUP_START a day and earns WARMUP_STEP more each day, up to DAILY_LIMIT.
OUTREACH_WARMUP_ENABLED = env_bool('OUTREACH_WARMUP_ENABLED', True)
OUTREACH_WARMUP_START = int(os.getenv('OUTREACH_WARMUP_START', '5'))
OUTREACH_WARMUP_STEP = int(os.getenv('OUTREACH_WARMUP_STEP', '2'))
# Follow-ups: days to wait after the previous email, one number per follow-up. Stops on reply/bounce/opt-out.
OUTREACH_FOLLOWUPS_ENABLED = env_bool('OUTREACH_FOLLOWUPS_ENABLED', True)
OUTREACH_FOLLOWUP_DAYS = os.getenv('OUTREACH_FOLLOWUP_DAYS', '3,4,7')
# Drafts below this playbook score (outreach/playbook.py) are rewritten by Gemini and never auto-sent.
OUTREACH_MIN_PLAYBOOK_SCORE = int(os.getenv('OUTREACH_MIN_PLAYBOOK_SCORE', '70'))
OUTREACH_HOURLY_LIMIT = int(os.getenv('OUTREACH_HOURLY_LIMIT', '5'))
OUTREACH_MIN_DELAY_SECONDS = int(os.getenv('OUTREACH_MIN_DELAY_SECONDS', '180'))
OUTREACH_MAX_DELAY_SECONDS = int(os.getenv('OUTREACH_MAX_DELAY_SECONDS', '480'))
OUTREACH_SEND_HOUR_START = int(os.getenv('OUTREACH_SEND_HOUR_START', '9'))
OUTREACH_SEND_HOUR_END = int(os.getenv('OUTREACH_SEND_HOUR_END', '17'))
OUTREACH_WEEKDAYS_ONLY = env_bool('OUTREACH_WEEKDAYS_ONLY', True)
OUTREACH_RECONTACT_DAYS = int(os.getenv('OUTREACH_RECONTACT_DAYS', '30'))
OUTREACH_MAX_LINKS = int(os.getenv('OUTREACH_MAX_LINKS', '2'))
OUTREACH_MAX_WORDS = int(os.getenv('OUTREACH_MAX_WORDS', '150'))
# Block approval when a draft has strong AI-writing tells (see outreach/humanizer.py).
OUTREACH_HUMANIZER_STRICT = env_bool('OUTREACH_HUMANIZER_STRICT', True)
# Email you every new draft with a review link (edit / approve / reject).
OUTREACH_NOTIFY_ON_DRAFT = env_bool('OUTREACH_NOTIFY_ON_DRAFT', True)
OUTREACH_NOTIFY_EMAIL = os.getenv('OUTREACH_NOTIFY_EMAIL', '') or OUTREACH_FROM_EMAIL
OUTREACH_REVIEW_BASE_URL = os.getenv('OUTREACH_REVIEW_BASE_URL', 'http://localhost:8000').rstrip('/')
OUTREACH_REVIEW_LINK_DAYS = int(os.getenv('OUTREACH_REVIEW_LINK_DAYS', '7'))
# One review email + one approval per batch of drafts.
OUTREACH_BATCH_REVIEW = env_bool('OUTREACH_BATCH_REVIEW', True)
OUTREACH_BATCH_QUIET_SECONDS = int(os.getenv('OUTREACH_BATCH_QUIET_SECONDS', '120'))
OUTREACH_BATCH_MAX = int(os.getenv('OUTREACH_BATCH_MAX', '100'))
# If you do not answer in time, emails that pass EVERY check are sent; anything uncertain is held.
OUTREACH_AUTO_SEND_ENABLED = env_bool('OUTREACH_AUTO_SEND_ENABLED', False)
OUTREACH_AUTO_SEND_AFTER_HOURS = float(os.getenv('OUTREACH_AUTO_SEND_AFTER_HOURS', '12'))
OUTREACH_AUTO_SEND_MIN_CONFIDENCE = float(os.getenv('OUTREACH_AUTO_SEND_MIN_CONFIDENCE', '0.9'))
OUTREACH_FREEMAIL_DOMAINS = env_list(
    'OUTREACH_FREEMAIL_DOMAINS',
    'gmail.com,googlemail.com,outlook.com,hotmail.com,hotmail.co.uk,live.com,live.co.uk,yahoo.com,'
    'yahoo.co.uk,icloud.com,me.com,aol.com,msn.com,proton.me,protonmail.com,btinternet.com,sky.com,'
    'talktalk.net,virginmedia.com',
)
# SerpAPI business check: personalises drafts, skips closed businesses, gates auto-send.
OUTREACH_RESEARCH_ENABLED = env_bool('OUTREACH_RESEARCH_ENABLED', True)
OUTREACH_RESEARCH_MAX_AGE_DAYS = float(os.getenv('OUTREACH_RESEARCH_MAX_AGE_DAYS', '3'))
OUTREACH_RESEARCH_DAILY_MAX = int(os.getenv('OUTREACH_RESEARCH_DAILY_MAX', '50'))
OUTREACH_PORTFOLIO_URL = os.getenv('OUTREACH_PORTFOLIO_URL', 'https://zubairhussain.xyz')
OUTREACH_OPT_OUT_LINE = os.getenv(
    'OUTREACH_OPT_OUT_LINE',
    "If this isn't relevant, just reply \"unsubscribe\" and I won't contact you again.",
)

SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', not DEBUG)
SESSION_COOKIE_SECURE = env_bool('SESSION_COOKIE_SECURE', not DEBUG)
CSRF_COOKIE_SECURE = env_bool('CSRF_COOKIE_SECURE', not DEBUG)
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '0' if DEBUG else '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', not DEBUG)
SECURE_HSTS_PRELOAD = env_bool('SECURE_HSTS_PRELOAD', not DEBUG)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
# The admin lives at a secret path in production (set ADMIN_URL=some-long-random-string/).
ADMIN_URL = os.getenv('ADMIN_URL', 'admin/' if DEBUG else 'admin/')
REFERRER_POLICY = 'same-origin'

# Logging - Console only for Docker
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'leads': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'outreach': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'leads.authentication.FallthroughJWTAuthentication',
        'leads.authentication.FirebaseAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    # JSON only in production: no browsable API page that documents the endpoints.
    'DEFAULT_RENDERER_CLASSES': (
        ['rest_framework.renderers.JSONRenderer', 'rest_framework.renderers.BrowsableAPIRenderer']
        if DEBUG else ['rest_framework.renderers.JSONRenderer']
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '60/hour',
        'user': '1000/hour',
    },
}

from datetime import timedelta  # noqa: E402

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(
        minutes=int(os.getenv('JWT_ACCESS_MINUTES', '15'))
    ),
    'REFRESH_TOKEN_LIFETIME': timedelta(
        days=int(os.getenv('JWT_REFRESH_DAYS', '7'))
    ),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

FIREBASE_PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID') or os.getenv('VITE_FIREBASE_PROJECT_ID')
LEADGEN_SYNC_REQUESTS = env_bool('LEADGEN_SYNC_REQUESTS', DEBUG)
MAX_VERIFY_UPLOAD_BYTES = int(os.getenv('MAX_VERIFY_UPLOAD_BYTES', str(5 * 1024 * 1024)))

if DEBUG:
    INTERNAL_IPS = [
        '127.0.0.1',
    ]
