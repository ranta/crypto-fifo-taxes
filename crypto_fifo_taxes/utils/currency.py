import time
from datetime import datetime
from decimal import Decimal
from functools import lru_cache
from typing import Optional, Union

import requests
from django.conf import settings

from crypto_fifo_taxes.models import Currency, CurrencyPair, CurrencyPrice


@lru_cache()
def get_default_fiat() -> Currency:
    """Return the currency object for default fiat currency"""
    return Currency.objects.get(is_fiat=True, symbol=settings.DEFAULT_FIAT_SYMBOL)


@lru_cache()
def get_currency(currency: Union[Currency, str, int]) -> Currency:
    if type(currency) == str:
        return Currency.objects.get(symbol__iexact=currency)
    if type(currency) == int:
        return Currency.objects.get(id=currency)
    return currency


@lru_cache()
def get_or_create_currency(currency: str) -> Currency:
    try:
        return get_currency(currency)
    except Currency.DoesNotExist:
        cg_currency_list = coingecko_get_currency_list()
        # In most cases symbols will match, but in a few cases where it doesn't the id should match. e.g. IOTA
        try:
            currency_data = next(
                filter(lambda x: x["symbol"] == currency.lower() or x["id"] == currency.lower(), cg_currency_list)
            )
        except StopIteration:
            raise f"Currency `{currency}` not found in CoinGecko API"

        assert currency_data
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


def retry_get_request_until_ok(url: str) -> Optional[dict]:
    while True:
        response = requests.get(url)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            # CoinGecko has a rate limit of 50 calls/minute, but In reality it seems to be more than that
            # If requests are throttled, wait and retry later
            sleep_time = int(response.headers["Retry-After"])
            print(f"Too Many Requests sent. Waiting {sleep_time}s until trying again")
            time.sleep(sleep_time)
            continue
        # Do not loop forever if response status is unexpected
        return None


@lru_cache()
def coingecko_get_currency_list() -> dict:
    """
    Can be cached because of large output and almost never changing

    Data format:
    {'id': 'bitcoin', 'symbol': 'btc', 'name': 'Bitcoin'}
    """
    api_url = "https://api.coingecko.com/api/v3/coins/list?include_platform=false"
    return retry_get_request_until_ok(api_url)


@lru_cache()
def coingecko_request_price_history(currency: Currency, date: datetime.date) -> Optional[dict]:
    """Requests and returns all data for given currency and date from CoinGecko API"""
    assert currency.cg_id is not None
    api_url = "https://api.coingecko.com/api/v3/coins/{id}/history?date={date}&localization=false".format(
        id=currency.cg_id,
        date=date.strftime("%d-%m-%Y"),
    )
    return retry_get_request_until_ok(api_url)


def fetch_currency_price(currency: Currency, date: datetime.date):
    """Update historical prices for given currency and date"""
    response_json = coingecko_request_price_history(currency, date)
    assert response_json is not None

    # FIXME: Save image locally
    # if currency.icon is None:
    #     currency.icon = response_json["image"]["small"]

    for fiat_symbol in settings.ALL_FIAT_CURRENCIES.keys():
        fiat_currency = get_or_create_currency(currency=fiat_symbol)
        CurrencyPrice.objects.update_or_create(
            currency=currency,
            fiat=fiat_currency,
            date=date,
            defaults=dict(
                price=Decimal(str(response_json["market_data"]["current_price"][fiat_symbol.lower()])),
                market_cap=Decimal(str(response_json["market_data"]["market_cap"][fiat_symbol.lower()])),
                volume=Decimal(str(response_json["market_data"]["total_volume"][fiat_symbol.lower()])),
            ),
        )
