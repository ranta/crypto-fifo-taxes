import logging
from functools import lru_cache

from django.conf import settings
from django.db import IntegrityError

from crypto_fifo_taxes.exceptions import CoinGeckoMissingCurrency, CoinGeckoMultipleMatchingCurrenciesCurrency
from crypto_fifo_taxes.models import Currency, CurrencyPair

logger = logging.getLogger(__name__)


@lru_cache
def get_default_fiat() -> Currency:
    """Return the currency object for default fiat currency"""
    return Currency.objects.get(is_fiat=True, symbol=settings.DEFAULT_FIAT_SYMBOL)


@lru_cache
def all_fiat_currencies() -> list[Currency]:
    fiat_currencies = Currency.objects.filter(is_fiat=True)

    if len(fiat_currencies) == len(settings.ALL_FIAT_CURRENCIES):
        return fiat_currencies

    # We are missing some currencies, create all required fiat currencies
    fiat_currencies = []
    for symbol, data in settings.ALL_FIAT_CURRENCIES.items():
        currency, _ = Currency.objects.get_or_create(
            symbol=symbol,
            defaults={"name": data["name"], "cg_id": data["cg_id"], "is_fiat": True},
        )
        fiat_currencies.append(currency)
    return fiat_currencies


@lru_cache
def get_currency(currency: Currency | str | int) -> Currency:
    """
    Return the currency object for the given symbol, id or object.
    If the currency is not found, raise an exception.
    """
    if isinstance(currency, Currency):
        return currency

    if isinstance(currency, int):
        return Currency.objects.get(id=currency)

    if isinstance(currency, str):
        symbol = currency.upper()

        try:
            return Currency.objects.get(symbol=symbol)
        except Currency.DoesNotExist:
            # Check if the symbol has been changed, and try to find the currency again with the new or legacy symbol
            if symbol in settings.RENAMED_SYMBOLS:
                # If the currency is the old symbol, find the new symbol
                symbol = settings.RENAMED_SYMBOLS[symbol]
                return Currency.objects.get(symbol__iexact=symbol)
            elif symbol in settings.RENAMED_SYMBOLS.values():
                # If the currency is the new symbol, find the old symbol
                renamed_keys = list(settings.RENAMED_SYMBOLS.keys())
                renamed_values = list(settings.RENAMED_SYMBOLS.values())
                symbol = renamed_keys[renamed_values.index(symbol)]
                return Currency.objects.get(symbol__iexact=symbol)
            else:
                raise

    return currency


def get_currency_data_from_coingecko_currency_list(symbol: str, cg_currency_list: dict) -> dict | None:
    # In most cases symbols will match, but in a few cases where it doesn't the id should match. e.g. IOTA
    def currency_filter(x: dict):
        """Find the first currency that matches the symbol or id CoinGecko API"""
        if "binance-peg" in x["id"]:  # Ignore Binance pegged tokens
            return False
        return x["symbol"] == symbol.lower() or x["id"] == symbol.lower()

    try:
        matches = list(filter(currency_filter, cg_currency_list))
        if len(matches) > 1:
            logger.error(
                f"Multiple matching currencies found for symbol '{symbol}' in CoinGecko API."
                f"The correct data should be manually entered to 'COINGECKO_MAPPED_CRYPTO_CURRENCIES': {matches}"
            )
            msg = f"Multiple currencies found for symbol '{symbol}' in CoinGecko API."
            raise CoinGeckoMultipleMatchingCurrenciesCurrency(msg)
        return next(filter(currency_filter, cg_currency_list))
    except StopIteration:
        # Currency was not found in CoinGecko currency list
        return None


@lru_cache
def get_coingecko_id_for_symbol(symbol: str) -> dict:
    """
    Return the CoinGecko API data for the given symbol.
    If the symbol is not found, raise an exception.
    """
    from crypto_fifo_taxes.utils.coingecko import coingecko_get_currency_list

    # Check if the symbol mapping is pre-defined in settings
    if symbol in settings.COINGECKO_MAPPED_CRYPTO_CURRENCIES:
        return {
            "id": settings.COINGECKO_MAPPED_CRYPTO_CURRENCIES[symbol]["cg_id"],
            "symbol": symbol,
            "name": settings.COINGECKO_MAPPED_CRYPTO_CURRENCIES[symbol]["name"],
        }

    cg_currency_list = coingecko_get_currency_list()

    currency_data = get_currency_data_from_coingecko_currency_list(symbol, cg_currency_list)
    if currency_data is not None:
        return currency_data

    if symbol in settings.COINGECKO_DEPRECATED_TOKENS:
        return {"id": None, "symbol": symbol, "name": None}

    raise CoinGeckoMissingCurrency(f"Currency `{symbol}` not found in CoinGecko API")


@lru_cache
def get_or_create_currency(symbol: str) -> Currency:
    """
    Return the currency object for the given symbol.
    If the currency does not exist, create it.
    """
    symbol = symbol.upper()
    if symbol in settings.RENAMED_SYMBOLS:
        symbol = settings.RENAMED_SYMBOLS[symbol]

    try:
        return get_currency(symbol)
    except Currency.DoesNotExist:
        currency_data: dict = get_coingecko_id_for_symbol(symbol)

        try:
            return Currency.objects.get_or_create(
                symbol=symbol,
                defaults={
                    "name": currency_data["name"],
                    "cg_id": currency_data["id"],
                },
            )[0]
        except IntegrityError:
            logger.warning(f"Currency `{symbol}` already exists in the database.")
            raise


@lru_cache
def get_or_create_currency_pair(symbol: str, buy: Currency | str, sell: Currency | str) -> CurrencyPair:
    return CurrencyPair.objects.get_or_create(
        symbol=symbol,
        defaults={
            "buy": get_or_create_currency(buy),
            "sell": get_or_create_currency(sell),
        },
    )[0]
