"""Configuración Django para CLIENTESD (Portal de Clientes - SETTEPI Pacífico).

Un solo archivo de settings con comportamiento dev/prod según DJANGO_ENV.
- dev  : SQLite, DEBUG, email en consola, sin Celery.
- prod : PostgreSQL, HTTPS, whitenoise, SMTP, Celery/Redis.
"""

from pathlib import Path

from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent

ENV = config("DJANGO_ENV", default="dev").lower()
IS_PROD = ENV == "prod"

SECRET_KEY = config("SECRET_KEY", default="dev-insecure-key-cambiar-en-prod")
DEBUG = config("DEBUG", default=(not IS_PROD), cast=bool)

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="localhost,127.0.0.1",
    cast=Csv(),
)
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost:8000",
    cast=Csv(),
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.core",
    "apps.bustrax",
    "apps.metricas",
    "apps.sync",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.ScopeMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.scope",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ------------------------------------------------------------------ Base de datos
if IS_PROD:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("POSTGRES_DB", default="clientesd"),
            "USER": config("POSTGRES_USER", default="clientesd"),
            "PASSWORD": config("POSTGRES_PASSWORD", default="clientesd"),
            "HOST": config("POSTGRES_HOST", default="db"),
            "PORT": config("POSTGRES_PORT", default="5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-mx"
TIME_ZONE = "America/Tijuana"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        if IS_PROD
        else "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ------------------------------------------------------------------ Auth
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "metricas:index"
LOGOUT_REDIRECT_URL = "login"

# ------------------------------------------------------------------ Email
if IS_PROD:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = config("EMAIL_HOST", default="")
    EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
    EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
    EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
    EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

DEFAULT_FROM_EMAIL = config(
    "DEFAULT_FROM_EMAIL", default="portalclientes@pacifico.mikecardona076.com"
)

# ------------------------------------------------------------------ APIs externas
BUSTRAX_IUSER = config("BUSTRAX_IUSER", default="LOGMIKE_TJ2")
BUSTRAX_VER_REPORTS = config("BUSTRAX_VER_REPORTS", default="1.1.0")
BUSTRAX_VER_JSON = config("BUSTRAX_VER_JSON", default="1.0.1")
BUSTRAX_TOKEN_TRIPS = config("BUSTRAX_TOKEN_TRIPS", default="")
BUSTRAX_TOKEN_MAE = config("BUSTRAX_TOKEN_MAE", default="")
BUSTRAX_URL_REPORTS = "https://api.bustrax.io/engine/get_reports.php"
BUSTRAX_URL_JSON = "https://api.bustrax.io/engine/get_json.php"
BUSTRAX_TIMEOUT = config("BUSTRAX_TIMEOUT", default=180, cast=int)

TRAFFILOG_BASE = config("TRAFFILOG_BASE", default="https://api.traffilog.mx/clients/json")
TRAFFILOG_USERNAME = config("TRAFFILOG_USERNAME", default="")
TRAFFILOG_PASSWORD = config("TRAFFILOG_PASSWORD", default="")
TRAFFILOG_TZ = config("TRAFFILOG_TZ", default="America/Tijuana")

CR_WINDOW_DEFAULT = config("CR_WINDOW_DEFAULT", default="14d")

# ------------------------------------------------------------------ Seguridad prod
if IS_PROD:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)

# ------------------------------------------------------------------ Celery (prod)
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://redis:6379/0")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default="redis://redis:6379/0")
CELERY_TIMEZONE = TIME_ZONE

try:  # celery no está instalado en dev
    from celery.schedules import crontab

    CELERY_BEAT_SCHEDULE = {
        "sync-semana-actual": {
            "task": "apps.sync.tasks.tarea_sync_semana_actual",
            "schedule": crontab(hour=5, minute=0),  # diario 05:00 (America/Tijuana)
        },
    }
except ImportError:
    CELERY_BEAT_SCHEDULE = {}
