import os

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
DEFAULT_FIAT_CURRENCY = {"name": "Euro", "cg_id": "eur"}


# Due to CoinGecko allowing multiple ids for the same currency, we need to map the ids to the correct currency.
# Not all currencies need to be mapped, but it helps to prevent errors when fetching prices.
# https://api.coingecko.com/api/v3/coins/list?include_platform=false
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
    "ALLO": {"name": "Allora", "cg_id": "allora"},
    "ALT": {"name": "AltLayer", "cg_id": "altlayer"},
    "ANC": {"name": "Anchor Protocol", "cg_id": "anchor-protocol"},
    "ANIME": {"name": "Animecoin", "cg_id": "anime"},
    "ATA": {"name": "ATA Token", "cg_id": "automata"},
    "ATOM": {"name": "Cosmos Hub", "cg_id": "cosmos"},
    "AVAX": {"name": "Avalanche", "cg_id": "avalanche-2"},
    "BABY": {"name": "Babylon", "cg_id": "babylon"},
    "BANANA": {"name": "Banana Gun", "cg_id": "banana-gun"},
    "BB": {"name": "BounceBit", "cg_id": "bouncebit"},
    "BCPT": {"name": "Blockmason Credit Protocol", "cg_id": "blockmason-credit-protocol"},  # Not in coingecko
    "BEL": {"name": "Bella Protocol", "cg_id": "bella-protocol"},
    "BETH": {"name": "Binance ETH staking", "cg_id": "binance-eth"},
    "BIO": {"name": "Bio Protocol", "cg_id": "bio-protocol"},
    "BMT": {"name": "Bubblemaps", "cg_id": "bubblemaps"},
    "BNB": {"name": "Binance Coin", "cg_id": "binancecoin"},
    "BTC": {"name": "Bitcoin", "cg_id": "bitcoin"},
    "BTCST": {"name": "BTC Standard Hashrate Token", "cg_id": "btc-standard-hashrate-token"},
    "CITY": {"name": "City Coin", "cg_id": "manchester-city-fan-token"},
    "CYBER": {"name": "CyberConnect", "cg_id": "cyberconnect"},
    "DAR": {"name": "Mines of Dalarnia", "cg_id": "mines-of-dalarnia"},
    "DODO": {"name": "DODO", "cg_id": "dodo"},
    "DOGE": {"name": "Dogecoin", "cg_id": "dogecoin"},
    "DOGS": {"name": "Dogs", "cg_id": "dogs-2"},
    "DOT": {"name": "Polkadot", "cg_id": "polkadot"},
    "EDEN": {"name": "OpenEden", "cg_id": "openeden"},
    "EDG": {"name": "Edgeware", "cg_id": "edgeware"},
    "ERA": {"name": "Caldera", "cg_id": "caldera"},
    "ETH": {"name": "Ethereum", "cg_id": "ethereum"},
    "ETHFI": {"name": "Ether.fi", "cg_id": "ether-fi"},
    "ETHW": {"name": "EthereumPoW", "cg_id": "ethereum-pow-iou"},
    "GAL": {"name": "Galatasaray Fan Token", "cg_id": "galatasaray-fan-token"},
    "GFT": {"name": "Gifto", "cg_id": "gifto"},  # Previously GTO
    "HBAR": {"name": "Hedera", "cg_id": "hedera-hashgraph"},
    "HFT": {"name": "Hashflow", "cg_id": "hashflow"},
    "HIGH": {"name": "Highstreet", "cg_id": "highstreet"},
    "HOLO": {"name": "Holoworld", "cg_id": "holoworld"},
    "HYPER": {"name": "Hyperlane", "cg_id": "hyperlane"},
    "ICP": {"name": "Internet Computer", "cg_id": "internet-computer"},
    "INIT": {"name": "Initia", "cg_id": "initia"},
    "IO": {"name": "io.net", "cg_id": "io"},
    "IOTA": {"name": "IOTA", "cg_id": "iota"},  # Previously MIOTA
    "KLAY": {"name": "Klaytn", "cg_id": "klay-token"},
    "LA": {"name": "Lagrange", "cg_id": "lagrange"},
    "LAYER": {"name": "Solayer", "cg_id": "solayer"},
    "LINK": {"name": "Chainlink", "cg_id": "chainlink"},
    "LIT": {"name": "Litentry", "cg_id": "litentry"},
    "LRC": {"name": "Loopring", "cg_id": "loopring"},
    "MANTA": {"name": "Manta Network", "cg_id": "manta-network"},
    "MATIC": {"name": "Polygon", "cg_id": "matic-network"},
    "MAV": {"name": "Maverick Protocol", "cg_id": "maverick-protocol"},
    "MBOX": {"name": "Mobox", "cg_id": "mobox"},
    "MC": {"name": "Merit Circle", "cg_id": "merit-circle"},
    "MEME": {"name": "Memecoin", "cg_id": "memecoin-2"},
    "MIRA": {"name": "Mira", "cg_id": "mira-2"},
    "MITO": {"name": "Mitosis", "cg_id": "mitosis"},
    "MMT": {"name": "Momentum", "cg_id": "momentum-3"},
    "MORPHO": {"name": "Morpho", "cg_id": "morpho"},
    "MOVE": {"name": "Movement", "cg_id": "movement"},
    "NAV": {"name": "Navcoin", "cg_id": "nav-coin"},
    "NEWT": {"name": "Newton Protocol", "cg_id": "newton-protocol"},
    "NFP": {"name": "NFPrompt", "cg_id": "nfprompt-token"},
    "NOT": {"name": "Notcoin", "cg_id": "notcoin"},
    "NTRN": {"name": "Neutron", "cg_id": "neutron-3"},
    "OMNI": {"name": "Omni Network", "cg_id": "omni-network"},
    "OPEN": {"name": "OpenLedger", "cg_id": "openledger-2"},
    "PENDLE": {"name": "Pendle", "cg_id": "pendle"},
    "PENGU": {"name": "Pudgy Penguins", "cg_id": "pudgy-penguins"},
    "PIXEL": {"name": "Pixels", "cg_id": "pixels"},
    "QI": {"name": "BENQI", "cg_id": "benqi"},
    "RDNT": {"name": "Radiant Capital", "cg_id": "radiant-capital"},
    "RED": {"name": "RedStone", "cg_id": "redstone-oracles"},
    "RVN": {"name": "Ravencoin", "cg_id": "ravencoin"},
    "SAGA": {"name": "Saga", "cg_id": "saga-2"},
    "SANTOS": {"name": "Santos FC Fan Token", "cg_id": "santos-fc-fan-token"},
    "SCR": {"name": "Scroll", "cg_id": "scroll"},
    "SEI": {"name": "Sei", "cg_id": "sei-network"},
    "SHELL": {"name": "MyShell", "cg_id": "myshell"},
    "SOL": {"name": "Solana", "cg_id": "solana"},
    "SOPH": {"name": "Sophon", "cg_id": "sophon"},
    "STRK": {"name": "Starknet", "cg_id": "starknet"},
    "SUI": {"name": "Sui", "cg_id": "sui"},
    "SXP": {"name": "Sxp", "cg_id": "swipe"},
    "THE": {"name": "Thena", "cg_id": "thena"},
    "TLM": {"name": "Alien Worlds", "cg_id": "alien-worlds"},
    "TON": {"name": "Toncoin", "cg_id": "the-open-network"},
    "TREE": {"name": "Treehouse", "cg_id": "treehouse"},
    "TURTLE": {"name": "Turtle", "cg_id": "turtle-2"},
    "USUAL": {"name": "Usual", "cg_id": "usual"},
    "VET": {"name": "VeChain", "cg_id": "vechain"},  # Previously VEN
    "VTHO": {"name": "VeThor", "cg_id": "vethor-token"},
    "WABI": {"name": "Wabi", "cg_id": "wabi"},  # No longer exists in Coingecko
    "WING": {"name": "Wing Finance", "cg_id": "wing-finance"},
    "XAI": {"name": "Xai", "cg_id": "xai-3"},
    "XLM": {"name": "Stellar", "cg_id": "stellar"},
    "XMR": {"name": "Monero", "cg_id": "monero"},
    "XNO": {"name": "Nano", "cg_id": "nano"},  # Previously NANO
    "XPL": {"name": "Plasma", "cg_id": "plasma"},
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
    "WABI",  # Wabi, Price is missing in Coingecko
    "BCPT",  # Blockmason Credit Protocol, Price is missing in Coingecko
    "1000CAT",  # Not found in Coingecko
}

# Sometimes the price is not found in CoinGecko, but the token still has value.
# These tokens are allowed to have missing prices.
COINGECKO_FLAKY_PRICES = {
    "AI",  # does not have a price for 2024-01-04
    "ALT",  # does not have a price for 2024-01-25
    "CYBER",  # does not have a price for 2023-08-03
    "ENA",
    "KAITO",  # does not have a price for 2025-02-19
    "MANTA",  # does not have a price for 2024-01-18
    "MAV",  # does not have a price for 2023-06-15
    "MEME",  # does not have a price for 2023-10-29
    "NFP",  # does not have a price for 2023-12-27
    "NOT",  # does not have a price for 2024-05-16
    "NTRN",  # does not have a price for 2023-10-12
    "PENDLE",  # does not have a price for 2023-07-05
    "RDNT",  # does not have a price for 2023-04-01
    "SCR",  # does not have a price for 2024-10-11
    "SUI",  # does not have a price for 2023-05-02
    "USUAL",  # does not have a price for 2024-11-19
    "RED",  # does not have a price for 2025-02-28
    "VET",
    "VTHO",
    "XAI",  # does not have a price for 2024-01-09
}

# The following symbols are ignored when importing dividends
IGNORED_TOKENS = [
    "JEX",  # Not worth anything, Coingecko doesn't even have any price history data on this
    "EDG",  # Unable to be traded in Binance
    "ETHW",  # Unable to be traded in Binance
]
