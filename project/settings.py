import os
from decimal import Decimal

import dj_database_url
import environ

env = environ.Env(DEBUG=(bool, False))
root = environ.Path(__file__) - 3
BASE_DIR = root()
DEBUG = env("DEBUG")
env.read_env(os.path.join(BASE_DIR, "app", ".env"))

SECRET_KEY = env("SECRET_KEY")

ALLOWED_HOSTS = env("ALLOWED_HOSTS", default="*").split(",")

DATABASES = {"default": dj_database_url.config()}

MEDIA_URL = env("MEDIA_URL", default="/media/")
STATIC_URL = env("STATIC_URL", default="/static/")

MEDIA_ROOT = root(env("MEDIA_LOCATION", default=os.path.join(BASE_DIR, "var", "media")))
STATIC_ROOT = root(env("STATIC_LOCATION", default=os.path.join(BASE_DIR, "var", "static")))

BINANCE_API_KEY = env("BINANCE_API_KEY")
BINANCE_API_SECRET = env("BINANCE_API_SECRET")

# Application definition

BASE_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

INSTALLED_APPS = BASE_APPS + [
    "crypto_fifo_taxes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
            "debug": DEBUG,
        },
    },
]

ROOT_URLCONF = "project.urls"
WSGI_APPLICATION = "project.wsgi.application"

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = "en"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# App settings
# Default FIAT currency. Used if when no other currency is defined
DEFAULT_FIAT_SYMBOL = "EUR"

# Save records for these currencies
ALL_FIAT_CURRENCIES = {"EUR": "Euro", "USD": "US Dollar"}

# The following symbols are ignored when importing dividends
IGNORED_TOKENS = [
    "JEX",  # Not worth anything, Coingecko doesn't even have any price history data on this
]

# Add coins currently in locked staking / locked savings, as they are not retrievable from any api endpoint
# These values are added to `get_binance_wallet_balance` output
# https://www.binance.com/en/my/wallet/account/saving
LOCKED_STAKING = {
    "BTC": Decimal("0.0"),
    "BNB": Decimal("0.0"),
}
