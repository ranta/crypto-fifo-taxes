import datetime
import logging
import time
from decimal import Decimal
from functools import lru_cache
from typing import TypedDict

import requests
from django.conf import settings
from django.utils import timezone

from crypto_fifo_taxes.exceptions import CoinGeckoAPIException, MissingPriceHistoryError
from crypto_fifo_taxes.models import Currency, CurrencyPrice
from crypto_fifo_taxes.utils.binance.binance_api import from_timestamp
from crypto_fifo_taxes.utils.currency import get_fiat_currency

logger = logging.getLogger(__name__)


def retry_get_request_until_ok(url: str) -> dict | None:
    while True:
        logger.debug(f"Fetching {url}")

        response = requests.get(url, timeout=10)

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
        elif response.status_code >= 400:
            raise CoinGeckoAPIException(f"Bad request to CoinGecko API url '{url}': {response.json()}")
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


class CoingeckoMarketChart(TypedDict):
    prices: list[list[int, float]]
    market_caps: list[list[int, float]]
    total_volumes: list[list[int, float]]


class MarketChartData(TypedDict):
    timestamp: datetime.datetime
    price: float
    market_cap: float
    volume: float


@lru_cache
def coingecko_request_market_chart(
    currency: Currency,
    vs_currency: Currency,
    start_date: datetime.date,
) -> CoingeckoMarketChart:
    assert currency.cg_id is not None
    assert vs_currency.cg_id is not None

    days = (timezone.now().date() - start_date).days + 1  # Add 1 to include end date (today)
    if days <= 0:
        raise ValueError("Start date should be before today.")

    api_url = (
        f"https://api.coingecko.com/api/v3/coins/{currency.cg_id}/market_chart?"
        f"vs_currency={vs_currency.cg_id}&days={days}&interval=daily"
    )
    logger.debug(
        f"Fetching market chart prices for {currency.symbol} "
        f"starting from {start_date} ({days} days) in {vs_currency.symbol}."
    )

    response_json = retry_get_request_until_ok(api_url)

    # Coin was unable to retrieved for some reason. e.g. deprecated (VEN)
    if response_json is None:
        # Retry once, as sometimes there are errors fetching data
        response_json = retry_get_request_until_ok(api_url)
        if response_json is None:
            raise MissingPriceHistoryError(f"Market chart not returned for {currency} starting from {start_date}.")

    if "prices" not in response_json:
        raise MissingPriceHistoryError(f"Market chart for {currency} starting from {start_date} didn't include prices.")

    return response_json


def fetch_currency_market_chart(currency: Currency) -> None:
    """Update historical prices for given currency and date using the CoinGecko API"""
    if (
        currency.is_fiat
        or currency.symbol in settings.COINGECKO_DEPRECATED_TOKENS
        or currency.symbol in settings.IGNORED_TOKENS
    ):
        logger.debug(f"Skipping currency {currency}.")
        return

    # First transaction date for the currency
    first_transaction_details = currency.transaction_details.order_by_timestamp().first()
    if first_transaction_details is None:
        logger.debug(f"Currency {currency} has no transactions, so we don't need to fetch historical prices for it.")
        return

    first_transaction_date = first_transaction_details.tx_timestamp.date()

    fiat_currency = get_fiat_currency()
    currency_price_qs = CurrencyPrice.objects.filter(
        currency=currency,
        date__gte=first_transaction_date,
    )

    # Days between first transaction and today
    total_num_days_required = (timezone.now().date() - first_transaction_date).days + 1  # Add 1 to include end date

    currency_prices_count = currency_price_qs.count()
    # If we have as many prices saved as the number of days between first transaction and today, we have all prices.
    if currency_prices_count == total_num_days_required:
        logger.debug(f"Already have all prices for {currency} in {fiat_currency.symbol}.")
        return

    # By default, start fetching prices from the first transaction date to get the prices for every single date.
    start_date = first_transaction_date

    # We have some prices saved, but not all. Check if we can fetch fewer days from the API.
    if currency_prices_count > 0:
        latest_currency_price: CurrencyPrice = currency_price_qs.order_by("-date").first()

        # If the CurrencyPrice has `num_missing_days`, we can deduct that from the total number of days required.
        # The prices were not returned from the API before, so they are not expected to be returned now,
        # making it pointless to try to fetch them again.
        adjusted_num_days_required = total_num_days_required - latest_currency_price.num_missing_days
        if currency_prices_count >= adjusted_num_days_required:
            logger.debug(f"Already have all prices for {currency} in {fiat_currency.symbol}.")
            return

        # Number of days we should have saved in the database.
        num_expected_prices_in_db = (latest_currency_price.date - first_transaction_date).days
        num_expected_prices_in_db -= latest_currency_price.num_missing_days

        # All dates between first_transaction_date and latest saved CurrencyPrice are in DB.
        if currency_prices_count >= num_expected_prices_in_db:
            # We can safely fetch currency prices starting from the first missing date.
            start_date = latest_currency_price.date + datetime.timedelta(days=1)

    try:
        response_json: CoingeckoMarketChart = coingecko_request_market_chart(currency, fiat_currency, start_date)
    except ValueError:
        return

    # Parse the response and to MarketChartData objects
    combined_market_chart_data = [
        MarketChartData(timestamp=from_timestamp(stamp), price=price, market_cap=market_cap, volume=volume)
        for (stamp, price), (__, market_cap), (__, volume) in zip(
            response_json["prices"], response_json["market_caps"], response_json["total_volumes"]
        )
    ]

    created_count = 0
    for market_chart_data in combined_market_chart_data:
        _, created = CurrencyPrice.objects.update_or_create(
            currency=currency,
            date=market_chart_data["timestamp"],
            defaults={
                "price": Decimal(str(market_chart_data["price"])),
                "market_cap": Decimal(str(market_chart_data["market_cap"])),
                "volume": Decimal(str(market_chart_data["volume"])),
            },
        )
        if created:
            created_count += 1
    if created_count > 0:
        logger.info(f"Created {created_count} new prices for {currency} in {fiat_currency.symbol}.")
    else:
        expected_created_count = (timezone.now().date() - start_date).days
        logger.warning(
            f"No new prices were created for {currency} in {fiat_currency.symbol}, "
            f"but {expected_created_count} new prices was expected. "
            f"Saving this result to reduce useless future price fetches."
        )

        latest_currency_price: CurrencyPrice = currency_price_qs.order_by("-date").first()
        if latest_currency_price is not None:
            latest_currency_price.num_missing_days = expected_created_count
            latest_currency_price.save()
        else:
            logger.error(
                f"No prices was returned for {currency} in {fiat_currency.symbol}. "
                f"Consider adding it to `COINGECKO_ASSUME_ZERO_PRICE_TOKENS` list."
            )
            return
