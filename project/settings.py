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

ALL_FIAT_CURRENCIES = {
    "EUR": {"name": "Euro", "cg_id": "eur"},
    "USD": {"name": "US Dollar", "cg_id": "usd"},
}

# Due to CoinGecko allowing multiple ids for the same currency, we need to map the ids to the correct currency.
# Not all currencies need to be mapped, but it helps to prevent errors when fetching prices.
COINGECKO_MAPPED_CRYPTO_CURRENCIES = {
    # STABLECOINS
    "USDT": {"name": "Tether", "cg_id": "tether"},
    "USDC": {"name": "USDC", "cg_id": "usd-coin"},
    "FDUSD": {"name": "First Digital USD", "cg_id": "first-digital-usd"},
    "BUSD": {"name": "Binance USD", "cg_id": "binance-usd"},
    # CRYPTO
    "AAVE": {"name": "Aave", "cg_id": "aave"},
    "ACE": {"name": "Fusionist", "cg_id": "endurance"},
    "ADA": {"name": "Cardano", "cg_id": "cardano"},
    "AI": {"name": "Sleepless AI", "cg_id": "sleepless-ai"},
    "ALICE": {"name": "My Neighbor Alice", "cg_id": "my-neighbor-alice"},
    "ALT": {"name": "AltLayer", "cg_id": "altlayer"},
    "ANC": {"name": "Anchor Protocol", "cg_id": "anchor-protocol"},
    "ATA": {"name": "ATA Token", "cg_id": "automata"},
    "ATOM": {"name": "Cosmos Hub", "cg_id": "cosmos"},
    "AVAX": {"name": "Avalanche", "cg_id": "avalanche-2"},
    "BCPT": {"name": "Blockmason Credit Protocol", "cg_id": "blockmason-credit-protocol"},  # Not in coingecko
    "BEL": {"name": "Bella Protocol", "cg_id": "bella-protocol"},
    "BETH": {"name": "Binance ETH staking", "cg_id": "binance-eth"},
    "BNB": {"name": "Binance Coin", "cg_id": "binancecoin"},
    "BTC": {"name": "Bitcoin", "cg_id": "bitcoin"},
    "BTCST": {"name": "BTC Standard Hashrate Token", "cg_id": "btc-standard-hashrate-token"},
    "CITY": {"name": "City Coin", "cg_id": "manchester-city-fan-token"},
    "CYBER": {"name": "CyberConnect", "cg_id": "cyberconnect"},
    "DAR": {"name": "Mines of Dalarnia", "cg_id": "mines-of-dalarnia"},
    "DODO": {"name": "DODO", "cg_id": "dodo"},
    "DOGE": {"name": "Dogecoin", "cg_id": "dogecoin"},
    "DOT": {"name": "Polkadot", "cg_id": "polkadot"},
    "EDG": {"name": "Edgeware", "cg_id": "edgeware"},
    "ETH": {"name": "Ethereum", "cg_id": "ethereum"},
    "ETHFI": {"name": "Ether.fi", "cg_id": "ether-fi"},
    "ETHW": {"name": "EthereumPoW", "cg_id": "ethereum-pow-iou"},
    "GAL": {"name": "Galatasaray Fan Token", "cg_id": "galatasaray-fan-token"},
    "GFT": {"name": "Gifto", "cg_id": "gifto"},  # Previously GTO
    "HBAR": {"name": "Hedera", "cg_id": "hedera-hashgraph"},
    "HFT": {"name": "Hashflow", "cg_id": "hashflow"},
    "HIGH": {"name": "Highstreet", "cg_id": "highstreet"},
    "ICP": {"name": "Internet Computer", "cg_id": "internet-computer"},
    "IOTA": {"name": "IOTA", "cg_id": "iota"},  # Previously MIOTA
    "KLAY": {"name": "Klaytn", "cg_id": "klay-token"},
    "LINK": {"name": "Chainlink", "cg_id": "chainlink"},
    "LIT": {"name": "Litentry", "cg_id": "litentry"},
    "LRC": {"name": "Loopring", "cg_id": "loopring"},
    "MANTA": {"name": "Manta Network", "cg_id": "manta-network"},
    "MATIC": {"name": "Polygon", "cg_id": "matic-network"},
    "MAV": {"name": "Maverick Protocol", "cg_id": "maverick-protocol"},
    "MBOX": {"name": "Mobox", "cg_id": "mobox"},
    "MC": {"name": "Merit Circle", "cg_id": "merit-circle"},
    "MEME": {"name": "Memecoin", "cg_id": "memecoin-2"},
    "NAV": {"name": "Navcoin", "cg_id": "nav-coin"},
    "NFP": {"name": "NFPrompt", "cg_id": "nfprompt-token"},
    "NTRN": {"name": "Neutron", "cg_id": "neutron-3"},
    "PENDLE": {"name": "Pendle", "cg_id": "pendle"},
    "PIXEL": {"name": "Pixels", "cg_id": "pixels"},
    "QI": {"name": "BENQI", "cg_id": "benqi"},
    "RDNT": {"name": "Radiant Capital", "cg_id": "radiant-capital"},
    "RVN": {"name": "Ravencoin", "cg_id": "ravencoin"},
    "SANTOS": {"name": "Santos FC Fan Token", "cg_id": "santos-fc-fan-token"},
    "SEI": {"name": "Sei", "cg_id": "sei-network"},
    "SOL": {"name": "Solana", "cg_id": "solana"},
    "STRK": {"name": "Starknet", "cg_id": "starknet"},
    "SUI": {"name": "Sui", "cg_id": "sui"},
    "SXP": {"name": "Sxp", "cg_id": "sxp"},
    "TLM": {"name": "Alien Worlds", "cg_id": "alien-worlds"},
    "VET": {"name": "VeChain", "cg_id": "vechain"},  # Previously VEN
    "VTHO": {"name": "VeThor", "cg_id": "vethor-token"},
    "WABI": {"name": "Wabi", "cg_id": "wabi"},  # No longer exists in Coingecko
    "WING": {"name": "Wing Finance", "cg_id": "wing-finance"},
    "XAI": {"name": "Xai", "cg_id": "xai-3"},
    "XLM": {"name": "Stellar", "cg_id": "stellar"},
    "XMR": {"name": "Monero", "cg_id": "monero"},
    "XNO": {"name": "Nano", "cg_id": "nano"},  # Previously NANO
    "XRP": {"name": "XRP", "cg_id": "ripple"},
}

# Symbols that have changed their symbols
# The old symbol is still used in Binance API, but new one is used in Coingecko.
# The old symbol is used in transactions, the new symbol is used when fetching coingecko data.
# format: {"old": "new"}
RENAMED_SYMBOLS = {
    "NANO": "XNO",
    "MIOTA": "IOTA",
    "GTO": "GFT",
    "VEN": "VET",
}

# Tokens that have been deprecated and are not found in CoinGecko anymore, but
# previously used to have some value and have existing trades, which means that they should still be imported.
COINGECKO_DEPRECATED_TOKENS = {
    "WABI"  # Wabi, Price is missing in Coingecko
    "BCPT"  # Blockmason Credit Protocol, Price is missing in Coingecko
}

# The following symbols are ignored when importing dividends
IGNORED_TOKENS = [
    "JEX",  # Not worth anything, Coingecko doesn't even have any price history data on this
    "EDG",  # Unable to be traded in Binance
]

# Add coins currently in locked staking / locked savings, as they are not retrievable from any api endpoint
# These values are added to `get_binance_wallet_balance` output
# https://www.binance.com/en/my/wallet/account/saving
LOCKED_STAKING = {
    "BTC": Decimal("0.0"),
    "BNB": Decimal("0.0"),
}
