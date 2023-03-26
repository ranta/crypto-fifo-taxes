from functools import lru_cache
from typing import Union

from django.conf import settings

from crypto_fifo_taxes.exceptions import CoinGeckoMissingCurrency
from crypto_fifo_taxes.models import Currency, CurrencyPair


@lru_cache()
def get_default_fiat() -> Currency:
    """Return the currency object for default fiat currency"""
    return Currency.objects.get(is_fiat=True, symbol=settings.DEFAULT_FIAT_SYMBOL)


@lru_cache()
def get_currency(currency: Union[Currency, str, int]) -> Currency:
    if currency in settings.RENAMED_SYMBOLS:
        currency = settings.RENAMED_SYMBOLS[currency]

    if type(currency) == str:
        return Currency.objects.get(symbol__iexact=currency)
    if type(currency) == int:
        return Currency.objects.get(id=currency)
    return currency


@lru_cache()
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

        return Currency.objects.get_or_create(
            symbol=currency_data["symbol"].upper(),
            defaults=dict(
                name=currency_data["name"],
                cg_id=currency_data["id"],
            ),
        )[0]


@lru_cache()
def get_or_create_currency_pair(symbol: str, buy: Union[Currency, str], sell: Union[Currency, str]) -> CurrencyPair:
    return CurrencyPair.objects.get_or_create(
        symbol=symbol,
        defaults=dict(
            buy=get_or_create_currency(buy) if type(buy) == str else buy,
            sell=get_or_create_currency(sell) if type(sell) == str else sell,
        ),
    )[0]
