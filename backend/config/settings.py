import os
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')

DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() == 'true'
RUNNING_TESTS = 'test' in sys.argv


def _require(name, hint=''):
    """A setting that production must not be allowed to guess at."""
    value = os.getenv(name, '')
    if value:
        return value
    if DEBUG or RUNNING_TESTS:
        return ''
    raise ImproperlyConfigured(f'{name} must be set when DJANGO_DEBUG is not true. {hint}'.strip())

SECRET_KEY = _require('DJANGO_SECRET_KEY', 'Generate one with django.core.management.utils.get_random_secret_key().')
if not SECRET_KEY:
    SECRET_KEY = 'development-only-secret-key-not-for-production'

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    if host.strip()
]
RENDER_EXTERNAL_HOSTNAME = os.getenv('RENDER_EXTERNAL_HOSTNAME', '')
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'rest_framework.authtoken',
    'accounts',
    'chat',
    'health',
    'progress',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
WSGI_APPLICATION = 'config.wsgi.application'

DB_NAME = os.getenv('DB_NAME', '')
if DB_NAME:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': DB_NAME,
            'USER': os.getenv('DB_USER', ''),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
            'CONN_MAX_AGE': int(os.getenv('DB_CONN_MAX_AGE', '0')),
            'OPTIONS': {'connect_timeout': int(os.getenv('DB_CONNECT_TIMEOUT', '10'))},
        }
    }
elif DEBUG or RUNNING_TESTS:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}
else:
    raise ImproperlyConfigured('DB_NAME must be set when DJANGO_DEBUG is not true.')

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        'CORS_ALLOWED_ORIGINS',
        'https://paxis-ai.vercel.app,http://localhost:5173,http://127.0.0.1:5173',
    ).split(',')
    if origin.strip()
]
CORS_ALLOWED_ORIGIN_REGEXES = (
    [r'^https://paxis-ai-[a-z0-9-]+\.vercel\.app$']
    if os.getenv('CORS_ALLOW_VERCEL_PREVIEWS', 'False').lower() == 'true'
    else []
)
CSRF_TRUSTED_ORIGINS = [origin for origin in CORS_ALLOWED_ORIGINS if origin.startswith('https://')]

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', '')
SERPER_API_KEY = os.getenv('SERPER_API_KEY', '')
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
GROQ_MODEL = os.getenv('GROQ_MODEL', '')

GEMINI_TIMEOUT_MS = int(os.getenv('GEMINI_TIMEOUT_MS', '45000'))
GEMINI_RETRY_ATTEMPTS = int(os.getenv('GEMINI_RETRY_ATTEMPTS', '2'))
GEMINI_RETRY_INITIAL_DELAY = float(os.getenv('GEMINI_RETRY_INITIAL_DELAY', '0.5'))
GEMINI_RETRY_MAX_DELAY = float(os.getenv('GEMINI_RETRY_MAX_DELAY', '4.0'))

GROQ_TIMEOUT_SECONDS = float(os.getenv('GROQ_TIMEOUT_SECONDS', '30.0'))
GROQ_RETRY_ATTEMPTS = int(os.getenv('GROQ_RETRY_ATTEMPTS', '1'))

SERPER_TIMEOUT_SECONDS = float(os.getenv('SERPER_TIMEOUT_SECONDS', '8.0'))
SERPER_RESULTS_PER_QUERY = int(os.getenv('SERPER_RESULTS_PER_QUERY', '5'))
SERPER_MAX_CONCURRENCY = int(os.getenv('SERPER_MAX_CONCURRENCY', '4'))
SERPER_MAX_TOPICS = int(os.getenv('SERPER_MAX_TOPICS', '12'))

LOG_LEVEL = os.getenv('DJANGO_LOG_LEVEL', 'DEBUG' if DEBUG else 'INFO').upper()
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'paxis': {
            '()': 'config.log_redaction.RedactingFormatter',
            'format': '%(asctime)s %(levelname)s %(name)s %(threadName)s %(message)s',
        },
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'paxis', 'stream': sys.stdout},
    },
    'root': {'handlers': ['console'], 'level': 'WARNING'},
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'chat': {'handlers': ['console'], 'level': LOG_LEVEL, 'propagate': False},
    },
}
