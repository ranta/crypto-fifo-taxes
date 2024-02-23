import logging
from functools import lru_cache

from django.conf import settings
from django.db import IntegrityError

from crypto_fifo_taxes.exceptions import CoinGeckoMissingCurrency
from crypto_fifo_taxes.models import Currency, CurrencyPair

logger = logging.getLogger(__name__)


@lru_cache
def get_default_fiat() -> Currency:
    """Return the currency object for default fiat currency"""
    return Currency.objects.get(is_fiat=True, symbol=settings.DEFAULT_FIAT_SYMBOL)


@lru_cache
def get_currency(currency: Currency | str | int) -> Currency:
    if isinstance(currency, Currency):
        return currency

    if isinstance(currency, int):
        return Currency.objects.get(id=currency)

    if isinstance(currency, str):
        currency = currency.upper()

        try:
            return Currency.objects.get(symbol=currency)
        except Currency.DoesNotExist:
            # Check if the symbol has been changed, and try to find the currency again with the new or legacy symbol
            if currency in settings.RENAMED_SYMBOLS:
                # If the currency is the old symbol, find the new symbol
                currency = settings.RENAMED_SYMBOLS[currency]
                return Currency.objects.get(symbol__iexact=currency)
            elif currency in settings.RENAMED_SYMBOLS.values():
                # If the currency is the new symbol, find the old symbol
                renamed_keys = list(settings.RENAMED_SYMBOLS.keys())
                renamed_values = list(settings.RENAMED_SYMBOLS.values())
                currency = renamed_keys[renamed_values.index(currency)]
                return Currency.objects.get(symbol__iexact=currency)
            else:
                raise

    return currency


@lru_cache
def get_or_create_currency(symbol: str) -> Currency:
    try:
        return get_currency(symbol)
    except Currency.DoesNotExist:
        from crypto_fifo_taxes.utils.coingecko import coingecko_get_currency_list

        cg_currency_list = coingecko_get_currency_list()
        # In most cases symbols will match, but in a few cases where it doesn't the id should match. e.g. IOTA
        try:

            def currency_filter(x):
                if "binance-peg" in x["id"]:
                    return False
                return x["symbol"] == symbol.lower() or x["id"] == symbol.lower()

            currency_data = next(filter(currency_filter, cg_currency_list))
        except StopIteration:
            if symbol.lower() in settings.DEPRECATED_TOKENS:
                currency_data = settings.DEPRECATED_TOKENS[symbol.lower()]
            else:
                raise CoinGeckoMissingCurrency(f"Currency `{symbol}` not found in CoinGecko API")

        assert currency_data

        if currency_data["symbol"].upper() in settings.RENAMED_SYMBOLS:
            symbol = settings.RENAMED_SYMBOLS[currency_data["symbol"].upper()]

        try:
            return Currency.objects.get_or_create(
                symbol=currency_data["symbol"].upper(),
                defaults={
                    "name": currency_data["name"],
                    "cg_id": currency_data["id"],
                },
            )[0]
        except IntegrityError:
            logger.warning(f"Currency `{currency_data['symbol'].upper()}` already exists in the database.")
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
