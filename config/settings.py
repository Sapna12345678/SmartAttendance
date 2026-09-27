from pathlib import Path


# ============================================================
# BASE DIRECTORY
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# ============================================================
# SECURITY
# ============================================================

SECRET_KEY = "django-insecure-@ocbzi@o3r#!nf-knj20$6s%s-p0d0l_$-c(7&=ywad))vbg9h8"

DEBUG = True


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

    # Current laptop Wi-Fi IP
    "10.11.120.160",

    "testserver",

    # All Cloudflare Quick Tunnel subdomains
    ".trycloudflare.com",
]


# ============================================================
# CSRF TRUSTED ORIGINS
# ============================================================
#
# Required for POST requests coming through Cloudflare HTTPS.
#
# Example:
# https://deaths-walking-european-these.trycloudflare.com
#
# The wildcard allows changing Quick Tunnel hostnames.
# ============================================================

CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://10.11.120.160:8000",

    # Cloudflare Quick Tunnel
    "https://*.trycloudflare.com",
]


# ============================================================
# CSRF COOKIE
# ============================================================

# JavaScript/fetch() attendance requests need access to the
# CSRF cookie.
CSRF_COOKIE_HTTPONLY = False

# Cloudflare terminates HTTPS and forwards the request to the
# local Django HTTP server during development.
CSRF_COOKIE_SECURE = False

# Allow CSRF cookie on the complete application.
CSRF_COOKIE_PATH = "/"


# ============================================================
# SESSION COOKIE
# ============================================================

# Development setup behind Cloudflare Quick Tunnel.
SESSION_COOKIE_SECURE = False

# Keep Django session cookie protected from JavaScript.
SESSION_COOKIE_HTTPONLY = True

SESSION_COOKIE_PATH = "/"


# ============================================================
# CLOUDFLARE HTTPS PROXY
# ============================================================

SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https"
)


# ============================================================
# SMART ATTENDANCE PUBLIC HOST
# ============================================================

if CURRENT_CLOUDFLARE_HOST:
    SMART_ATTENDANCE_HOST = CURRENT_CLOUDFLARE_HOST
else:
    SMART_ATTENDANCE_HOST = "127.0.0.1:8000"


# ============================================================
# COLLEGE ATTENDANCE LOCATION
# ============================================================

ATTENDANCE_LATITUDE = 25.342787

ATTENDANCE_LONGITUDE = 81.902116

# Allowed attendance radius in meters
ATTENDANCE_RADIUS_METERS = 300


# ============================================================
# INSTALLED APPS
# ============================================================

INSTALLED_APPS = [

    # Django built-in apps

    "django.contrib.admin",

    "django.contrib.auth",

    "django.contrib.contenttypes",

    "django.contrib.sessions",

    "django.contrib.messages",

    "django.contrib.staticfiles",

    # Smart Attendance application

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

STATIC_URL = "static/"


# ============================================================
# MEDIA FILES
# ============================================================

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


# ============================================================
# EMAIL
# ============================================================
#
# Development mode:
# Password-reset emails etc. appear in the Django terminal.
#
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