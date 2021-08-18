import time
from datetime import datetime
from decimal import Decimal
from functools import lru_cache
from typing import Optional, Union

import requests
from django.conf import settings
from django.utils.text import slugify

from crypto_fifo_taxes.models import Currency, CurrencyPrice


@lru_cache()
def get_default_fiat() -> Currency:
    """Return the currency object for default fiat currency"""
    return Currency.objects.get(is_fiat=True, symbol=settings.DEFAULT_FIAT_CURRENCY)


@lru_cache()
def get_currency(currency: Union[Currency, str, int]) -> Currency:
    if type(currency) == str:
        return Currency.objects.get(symbol=currency)
    if type(currency) == int:
        return Currency.objects.get(id=currency)
    return currency


@lru_cache()
def get_or_create_currency(currency: str) -> Currency:
    try:
        return get_currency(currency)
    except Currency.DoesNotExist:
        currency_data = next(filter(lambda x: x["symbol"] == currency, coingecko_get_currency_list()))
        assert currency_data
        return Currency.objects.get_or_create(
            symbol=currency_data["symbol"],
            defaults=dict(
                name=currency_data["name"],
                cg_id=currency_data["id"],
            ),
        )[0]


@lru_cache()
def coingecko_get_currency_list() -> dict:
    """
    Can be cached because of large output and almost never changing

    Data format:
    {'id': 'bitcoin', 'symbol': 'btc', 'name': 'Bitcoin'}
    """
    api_url = "https://api.coingecko.com/api/v3/coins/list?include_platform=false"
    response = requests.get(api_url)
    return response.json()


def coingecko_request_price_history(currency: Currency, date: datetime.date) -> Optional[dict]:
    """Requests and returns all data for given currency and date from CoinGecko API"""
    api_url = "https://api.coingecko.com/api/v3/coins/{id}/history?date={date}&localization=false".format(
        id=slugify(currency.name.lower()),
        date=date.strftime("%d-%m-%Y"),
    )
    response = None
    while response is None:
        response = requests.get(api_url)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            # CoinGecko has a rate limit of 50 calls/minute (In reality seems to be more)
            # If requests are throttled, wait and retry later
            time.sleep(int(response.headers["Retry-After"]))
            continue
        return None  # Do not loop forever if response status is unexpected


def fetch_currency_price(currency: Currency, date: datetime.date):
    """Update historical prices for given currency and date"""
    response_json = coingecko_request_price_history(currency, date)

    # FIXME: Save image locally
    # if currency.icon is None:
    #     currency.icon = response_json["image"]["small"]

    for fiat_symbol in settings.ALL_FIAT_CURRENCIES:
        fiat_currency = Currency.objects.get(symbol=fiat_symbol)
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
    currency.save()
