"""
MediAid settings.

Works locally (SQLite, or any PostgreSQL) and on Vercel + Neon with no code changes.
All secrets come from environment variables (.env locally, Vercel dashboard in production).
"""
import os
import sys
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_list(name, default=""):
    return [x.strip() for x in os.environ.get(name, default).split(",") if x.strip()]


RUNNING_TESTS = len(sys.argv) > 1 and sys.argv[1] == "test"
DEBUG = os.environ.get("DEBUG", "False").lower() in ("1", "true", "yes")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not (DEBUG or RUNNING_TESTS):
        raise ImproperlyConfigured("Set DJANGO_SECRET_KEY (see .env.example).")
    SECRET_KEY = "dev-only-insecure-key"

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1,.vercel.app")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "https://*.vercel.app")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "core",
    "medicines",
    "emergency",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "core.middleware.BanglaFirstLocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
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
                "django.template.context_processors.i18n",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------- Database
# Production: DATABASE_URL = your Neon *pooled* connection string.
# Local: leave it empty to use SQLite. Search still works there, but the spelling-mistake
# matching (trigram search) only runs on PostgreSQL.
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    DATABASES = {
        # Keep connections open between requests; health checks drop one that Neon closed while idle.
        "default": dj_database_url.parse(DATABASE_URL, conn_max_age=300, conn_health_checks=True)
    }
    # Neon's pooler (PgBouncer, transaction mode) does not support server-side cursors
    DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True
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

# ---------------------------------------------------------------- Language
# Bangla is the default for everyone, even if their browser is set to English.
# The toggle in the header stores the choice in the "django_language" cookie.
# Translations: locale/bn/LC_MESSAGES/django.po -> run `python manage.py compile_po` after editing.
LANGUAGE_CODE = "bn"
LANGUAGES = [("bn", _("Bangla")), ("en", _("English"))]
LOCALE_PATHS = [BASE_DIR / "locale"]
LANGUAGE_COOKIE_AGE = 60 * 60 * 24 * 365
TIME_ZONE = "Asia/Dhaka"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------- Static files
# On Vercel: STATIC_ROOT makes the build run collectstatic, and the CDN serves the files.
# Hashed file names mean a changed CSS file reaches visitors straight away.
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
if not (DEBUG or RUNNING_TESTS):
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# The largest CSV the admin page accepts. Vercel itself refuses uploads above about 4.5 MB;
# bigger files are loaded with `python manage.py import_csv`.
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# ---------------------------------------------------------------- Security (production)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
