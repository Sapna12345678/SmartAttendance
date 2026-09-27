from pathlib import Path
import os
import dj_database_url


# ============================================================
# BASE DIRECTORY
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# ============================================================
# SECURITY
# ============================================================

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-local-development-key"
)

DEBUG = os.environ.get("DEBUG", "True").lower() == "true"


# ============================================================
# CLOUDFLARE QUICK TUNNEL
# ============================================================

CLOUDFLARE_URL_FILE = BASE_DIR / "cloudflare_url.txt"


def get_cloudflare_host():
    """
    Read the current Cloudflare Quick Tunnel hostname
    from cloudflare_url.txt.
    """

    try:
        host = CLOUDFLARE_URL_FILE.read_text(
            encoding="utf-8"
        ).strip()

        if host.startswith("https://"):
            host = host[8:]

        elif host.startswith("http://"):
            host = host[7:]

        return host.rstrip("/")

    except (FileNotFoundError, OSError):
        return ""


CURRENT_CLOUDFLARE_HOST = get_cloudflare_host()


# ============================================================
# ALLOWED HOSTS
# ============================================================

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "testserver",
    "10.11.120.160",
    ".trycloudflare.com",
]


# Render public host
RENDER_HOST = os.environ.get("RENDER_EXTERNAL_HOSTNAME")

if RENDER_HOST:
    ALLOWED_HOSTS.append(RENDER_HOST)


# Additional hosts from environment
EXTRA_ALLOWED_HOSTS = os.environ.get(
    "ALLOWED_HOSTS",
    ""
)

if EXTRA_ALLOWED_HOSTS:
    ALLOWED_HOSTS.extend(
        host.strip()
        for host in EXTRA_ALLOWED_HOSTS.split(",")
        if host.strip()
    )


# ============================================================
# CSRF TRUSTED ORIGINS
# ============================================================

CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://10.11.120.160:8000",
    "https://*.trycloudflare.com",
]


if RENDER_HOST:
    CSRF_TRUSTED_ORIGINS.append(
        f"https://{RENDER_HOST}"
    )


EXTRA_CSRF_ORIGINS = os.environ.get(
    "CSRF_TRUSTED_ORIGINS",
    ""
)

if EXTRA_CSRF_ORIGINS:
    CSRF_TRUSTED_ORIGINS.extend(
        origin.strip()
        for origin in EXTRA_CSRF_ORIGINS.split(",")
        if origin.strip()
    )


# ============================================================
# CSRF COOKIE
# ============================================================

CSRF_COOKIE_HTTPONLY = False

CSRF_COOKIE_SECURE = not DEBUG

CSRF_COOKIE_PATH = "/"


# ============================================================
# SESSION COOKIE
# ============================================================

SESSION_COOKIE_SECURE = not DEBUG

SESSION_COOKIE_HTTPONLY = True

SESSION_COOKIE_PATH = "/"


# ============================================================
# HTTPS / PROXY
# ============================================================

SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https"
)


# ============================================================
# SMART ATTENDANCE PUBLIC HOST
# ============================================================

if os.environ.get("SMART_ATTENDANCE_HOST"):
    SMART_ATTENDANCE_HOST = os.environ.get(
        "SMART_ATTENDANCE_HOST"
    )

elif RENDER_HOST:
    SMART_ATTENDANCE_HOST = RENDER_HOST

elif CURRENT_CLOUDFLARE_HOST:
    SMART_ATTENDANCE_HOST = CURRENT_CLOUDFLARE_HOST

else:
    SMART_ATTENDANCE_HOST = "127.0.0.1:8000"


# ============================================================
# COLLEGE ATTENDANCE LOCATION
# ============================================================

ATTENDANCE_LATITUDE = 25.342787

ATTENDANCE_LONGITUDE = 81.902116

ATTENDANCE_RADIUS_METERS = 300


# ============================================================
# INSTALLED APPS
# ============================================================

INSTALLED_APPS = [

    "django.contrib.admin",

    "django.contrib.auth",

    "django.contrib.contenttypes",

    "django.contrib.sessions",

    "django.contrib.messages",

    "django.contrib.staticfiles",

    "attendance.apps.AttendanceConfig",
]


# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [

    "django.middleware.security.SecurityMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",

    "django.middleware.common.CommonMiddleware",

    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",

    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ============================================================
# URL CONFIGURATION
# ============================================================

ROOT_URLCONF = "config.urls"


# ============================================================
# TEMPLATES
# ============================================================

TEMPLATES = [

    {
        "BACKEND":
            "django.template.backends.django.DjangoTemplates",

        "DIRS": [],

        "APP_DIRS": True,

        "OPTIONS": {

            "context_processors": [

                "django.template.context_processors.request",

                "django.contrib.auth.context_processors.auth",

                "django.contrib.messages.context_processors.messages",

            ],
        },
    },
]


# ============================================================
# WSGI
# ============================================================

WSGI_APPLICATION = "config.wsgi.application"


# ============================================================
# DATABASE
# ============================================================

DATABASE_URL = os.environ.get("DATABASE_URL")


if DATABASE_URL:

    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }

else:

    DATABASES = {

        "default": {

            "ENGINE":
                "django.db.backends.sqlite3",

            "NAME":
                BASE_DIR / "db.sqlite3",
        }
    }


# ============================================================
# PASSWORD VALIDATION
# ============================================================

AUTH_PASSWORD_VALIDATORS = [

    {
        "NAME":
            "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },

    {
        "NAME":
            "django.contrib.auth.password_validation.MinimumLengthValidator",
    },

    {
        "NAME":
            "django.contrib.auth.password_validation.CommonPasswordValidator",
    },

    {
        "NAME":
            "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# ============================================================
# LANGUAGE
# ============================================================

LANGUAGE_CODE = "en-us"


# ============================================================
# TIME ZONE
# ============================================================

TIME_ZONE = "Asia/Kolkata"

USE_I18N = True

USE_TZ = True


# ============================================================
# STATIC FILES
# ============================================================

STATIC_URL = "/static/"

STATIC_ROOT = BASE_DIR / "staticfiles"


# ============================================================
# MEDIA FILES
# ============================================================

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


# ============================================================
# EMAIL
# ============================================================

EMAIL_BACKEND = (
    "django.core.mail.backends.console.EmailBackend"
)


# ============================================================
# LOGIN / LOGOUT
# ============================================================

LOGIN_URL = "/accounts/login/"

LOGIN_REDIRECT_URL = "/accounts/dashboard/"

LOGOUT_REDIRECT_URL = "/accounts/login/"


# ============================================================
# DEFAULT PRIMARY KEY
# ============================================================

DEFAULT_AUTO_FIELD = (
    "django.db.models.BigAutoField"
)


# ============================================================
# PRODUCTION SECURITY
# ============================================================

if not DEBUG:

    SECURE_SSL_REDIRECT = True

    SECURE_HSTS_SECONDS = 31536000

    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

    SECURE_HSTS_PRELOAD = True

    SECURE_CONTENT_TYPE_NOSNIFF = True

    SECURE_REFERRER_POLICY = "same-origin"

    X_FRAME_OPTIONS = "DENY"