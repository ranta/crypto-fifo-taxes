import time
from datetime import datetime
from decimal import Decimal
from functools import lru_cache
from typing import Optional

import requests
from django.conf import settings

from crypto_fifo_taxes.exceptions import MissingPriceError
from crypto_fifo_taxes.models import Currency, CurrencyPrice
from crypto_fifo_taxes.utils.currency import get_or_create_currency


class CoinGeckoMissingCurrency(Exception):
    pass


def retry_get_request_until_ok(url: str) -> Optional[dict]:
    while True:
        response = requests.get(url)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            # CoinGecko has a rate limit of 50 calls/minute, but In reality it seems to be more than that
            # If requests are throttled, wait and retry later
            # For some reason the `"Retry-After"` is not always returned with a HTTP 429 response
            sleep_time = int(response.headers["Retry-After"]) if "Retry-After" in response.headers else 5
            print(f"Too Many Requests sent to CoinGecko API. Waiting {sleep_time}s until trying again")
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
    """Update historical prices for given currency and date using the CoinGecko API"""
    response_json = coingecko_request_price_history(currency, date)

    # Coin was unable to retrieved for some reason. e.g. deprecated (VEN)
    if response_json is None:
        if currency.symbol in settings.DEPRECATED_TOKENS:
            return
        raise MissingPriceError(f"Price not returned for {currency} on {date}")

    # Coin was returned, but has no market data for the date. Maybe the coin is "too new"? (VTHO)
    if "market_data" not in response_json:
        for fiat_symbol in settings.ALL_FIAT_CURRENCIES.keys():
            fiat_currency = get_or_create_currency(fiat_symbol)
            CurrencyPrice.objects.update_or_create(
                currency=currency, fiat=fiat_currency, date=date, defaults=dict(price=0, market_cap=0, volume=0)
            )
        return

    # FIXME: Save image locally
    # if currency.icon is None:
    #     currency.icon = response_json["image"]["small"]

    for fiat_symbol in settings.ALL_FIAT_CURRENCIES.keys():
        fiat_currency = get_or_create_currency(fiat_symbol)
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
