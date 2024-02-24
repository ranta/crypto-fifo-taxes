import os
from decimal import Decimal

import dj_database_url
import environ

env = environ.Env(DEBUG=(bool, False))
root = environ.Path(__file__) - 2
BASE_DIR = root()
DEBUG = env("DEBUG")
env.read_env(os.path.join(BASE_DIR, ".env"))

SECRET_KEY = os.environ.get("SECRET_KEY", "xxx")

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")

DATABASES = {"default": dj_database_url.config()}

MEDIA_URL = os.environ.get("MEDIA_URL", "/media/")
STATIC_URL = os.environ.get("STATIC_URL", "/static/")

MEDIA_ROOT = root(os.environ.get("MEDIA_LOCATION", os.path.join(BASE_DIR, "media")))
STATIC_ROOT = root(os.environ.get("STATIC_LOCATION", os.path.join(BASE_DIR, "static")))

BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY", None)
BINANCE_API_SECRET = os.environ.get("BINANCE_API_SECRET", None)

ETHPLORER_API_KEY = os.environ.get("ETHPLORER_API_KEY", None)

# Application definition

BASE_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

INSTALLED_APPS = [
    *BASE_APPS,
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
ALL_FIAT_CURRENCIES = {
    "EUR": {"name": "Euro", "cg_id": "eur"},
    "USD": {"name": "US Dollar", "cg_id": "usd"},
}

# The following symbols are ignored when importing dividends
IGNORED_TOKENS = [
    "JEX",  # Not worth anything, Coingecko doesn't even have any price history data on this
    "EDG",  # Unable to be traded in Binance
]

# The following symbols are ignored when getting prices from coingecko, a price of 0 is assumed instead
COINGECKO_ASSUME_ZERO_PRICE_TOKENS = [
    "MC",  # Margin-call - Price is missing in Coingecko
]

# Tokens that have been deprecated and are not found in CoinGecko anymore, but still have trades that should be imported
DEPRECATED_TOKENS = {
    "ven": {"id": "vechain-old", "symbol": "ven", "name": "VeChain OLD"},
    "wabi": {"id": "wabi", "symbol": "wabi", "name": "Wabi"},  # Price is missing in Coingecko
    "bcpt": {"id": "bcpt", "symbol": "bcpt", "name": "Blockmason Credit Protocol"},  # Price is missing in Coingecko
}

# Symbols that have changed their symbols
# The old symbol is still used in Binance API, but new one is used in Coingecko.
# The old symbol is used in transactions, the new symbol is used when fetching coingecko data.
# format: {"old": "new"}
RENAMED_SYMBOLS = {
    "NANO": "XNO",
    "MIOTA": "IOTA",
    "GTO": "GFT",
}


# Add coins currently in locked staking / locked savings, as they are not retrievable from any api endpoint
# These values are added to `get_binance_wallet_balance` output
# https://www.binance.com/en/my/wallet/account/saving
LOCKED_STAKING = {
    "BTC": Decimal("0.0"),
    "BNB": Decimal("0.0"),
}
