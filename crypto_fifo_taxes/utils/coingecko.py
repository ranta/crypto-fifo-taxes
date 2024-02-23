import logging
import time
from collections import namedtuple
import datetime
from decimal import Decimal
from functools import lru_cache

import requests
from django.conf import settings
from django.utils import timezone

from crypto_fifo_taxes.exceptions import MissingPriceError
from crypto_fifo_taxes.models import Currency, CurrencyPrice
from crypto_fifo_taxes.utils.binance.binance_api import from_timestamp
from crypto_fifo_taxes.utils.currency import get_currency, get_or_create_currency

logger = logging.getLogger(__name__)

MarketChartData = namedtuple("MarketChartData", "timestamp price market_cap volume")


def retry_get_request_until_ok(url: str) -> dict | None:
    while True:
        response = requests.get(url)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            # CoinGecko has a rate limit of 50 calls/minute, but In reality it seems to be more than that
            # If requests are throttled, wait and retry later
            # For some reason the `"Retry-After"` is not always returned with a HTTP 429 response
            sleep_time = int(response.headers["Retry-After"]) if "Retry-After" in response.headers else 5
            logger.warning(f"Too Many Requests sent to CoinGecko API. Waiting {sleep_time}s until trying again")
            time.sleep(sleep_time)
            continue
        # Do not loop forever if response status is unexpected
        return None


@lru_cache
def coingecko_get_currency_list() -> dict:
    """
    Can be cached because of large output and almost never changing

    Data format:
    {'id': 'bitcoin', 'symbol': 'btc', 'name': 'Bitcoin'}
    """
    api_url = "https://api.coingecko.com/api/v3/coins/list?include_platform=false"
    return retry_get_request_until_ok(api_url)


@lru_cache
def coingecko_request_price_history(currency: Currency, date: datetime.date) -> dict | None:
    """Requests and returns all data for given currency and date from CoinGecko API"""
    assert currency.cg_id is not None
    api_url = "https://api.coingecko.com/api/v3/coins/{id}/history?date={date}&localization=false".format(
        id=currency.cg_id,
        date=date.strftime("%d-%m-%Y"),
    )
    return retry_get_request_until_ok(api_url)


@lru_cache
def coingecko_request_market_chart(currency: Currency, vs_currency: Currency, start_date: datetime.date) -> dict:
    assert currency.cg_id is not None
    assert vs_currency.cg_id is not None

    days = (datetime.now().date() - start_date).days
    api_url = (
        f"https://api.coingecko.com/api/v3/coins/{currency.cg_id}/market_chart?"
        f"vs_currency={vs_currency.cg_id}&days={days}&interval=daily"
    )
    return retry_get_request_until_ok(api_url)


def fetch_currency_price(currency: Currency, date: datetime.date):
    """Update historical prices for given currency and date using the CoinGecko API"""
    response_json = coingecko_request_price_history(currency, date)

    # Coin was unable to retrieved for some reason. e.g. deprecated (VEN)
    if response_json is None:
        if currency.symbol in settings.DEPRECATED_TOKENS:
            return
        # Note: Sometimes price is returned for a currency for no reason, trying again might help
        raise MissingPriceError(f"Price not returned for {currency} on {date}")

    # Coin was returned, but has no market data for the date. Maybe the coin is "too new"? (VTHO)
    if "market_data" not in response_json:
        for fiat_symbol in settings.ALL_FIAT_CURRENCIES:
            fiat_currency = get_currency(fiat_symbol)
            CurrencyPrice.objects.update_or_create(
                currency=currency, fiat=fiat_currency, date=date, defaults={"price": 0, "market_cap": 0, "volume": 0}
            )
        return

    # FIXME: Save image locally
    # if currency.icon is None:
    #     currency.icon = response_json["image"]["small"]

    for fiat_symbol in settings.ALL_FIAT_CURRENCIES:
        fiat_currency = get_or_create_currency(fiat_symbol)
        CurrencyPrice.objects.update_or_create(
            currency=currency,
            fiat=fiat_currency,
            date=date,
            defaults={
                "price": Decimal(str(response_json["market_data"]["current_price"][fiat_symbol.lower()])),
                "market_cap": Decimal(str(response_json["market_data"]["market_cap"][fiat_symbol.lower()])),
                "volume": Decimal(str(response_json["market_data"]["total_volume"][fiat_symbol.lower()])),
            },
        )


def fetch_currency_market_chart(currency: Currency, start_date: datetime.date | None = None):
    """Update historical prices for given currency and date using the CoinGecko API"""
    if currency.is_fiat:
        return

    # Use the date of the first transaction with the currency as the default start date
    if start_date is None:
        if (first_detail := currency.transaction_details.order_by("tx_timestamp").first()) is not None:
            start_date = first_detail.tx_timestamp.date()

    if currency.symbol.lower() in settings.DEPRECATED_TOKENS:
        return

    if currency.symbol in settings.COINGECKO_ASSUME_ZERO_PRICE_TOKENS:
        return

    for fiat_symbol in settings.ALL_FIAT_CURRENCIES:
        fiat = get_currency(fiat_symbol)
        currency_price_qs = CurrencyPrice.objects.filter(fiat=fiat, currency=currency, date__gte=start_date)

        # Check if required prices already exist in db
        existing_prices_count = currency_price_qs.count()
        delta_days = (timezone.now().date() - start_date).days + 1
        if existing_prices_count == delta_days:
            continue

        # Check if we can query less dates than was requested
        latest_currency_price = currency_price_qs.order_by("-date").first()
        if latest_currency_price is not None:
            existing_prices_count = currency_price_qs.filter(date__lt=latest_currency_price.date).count()
            delta_days = (latest_currency_price.date - start_date).days + 1
            if existing_prices_count == delta_days:
                # We already have all dates between given start_date and latest saved CurrencyPrice saved in DB
                # Only fetch prices for dates after latest saved CurrencyPrice
                start_date = latest_currency_price.date

        response_json = coingecko_request_market_chart(currency, fiat, start_date)

        # Coin was unable to retrieved for some reason. e.g. deprecated (VEN)
        if response_json is None:
            # Retry once, as sometimes there are errors fetching data
            response_json = coingecko_request_market_chart(currency, fiat, start_date)
            if response_json is None:
                raise MissingPriceError(f"Market chart not returned for {currency} starting from {start_date}.")

        if "prices" not in response_json:
            raise MissingPriceError(f"Market chart for {currency} starting from {start_date} didn't include prices.")

        combined_market_data = [
            MarketChartData(stamp, price, cap, volume)
            for (stamp, price), (__, cap), (__, volume) in zip(
                response_json["prices"], response_json["market_caps"], response_json["total_volumes"]
            )
        ]
        for market_data in combined_market_data:
            CurrencyPrice.objects.update_or_create(
                currency=currency,
                fiat=fiat,
                date=from_timestamp(market_data.timestamp),
                defaults={
                    "price": Decimal(str(market_data.price)),
                    "market_cap": Decimal(str(market_data.market_cap)),
                    "volume": Decimal(str(market_data.volume)),
                },
            )
