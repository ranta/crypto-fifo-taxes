import logging
import time
from collections.abc import Callable, Iterator
from datetime import datetime, timedelta
from functools import lru_cache

import pytz
from binance.exceptions import BinanceAPIException
from django.conf import settings

from crypto_fifo_taxes.exceptions import TooManyResultsError
from crypto_fifo_taxes.utils.binance.binance_client import BinanceClient
from crypto_fifo_taxes.utils.binance.types import (
    BinanceFlexibleInterest,
    BinanceFlexibleInterestHistoryResponse,
    BinanceLockedInterest,
    BinanceLockedInterestHistoryResponse,
)

logger = logging.getLogger(__name__)


def to_timestamp(dt: datetime) -> int:
    """datetime to Binance-timestamp"""
    return int(datetime.timestamp(dt)) * 1000


def from_timestamp(stamp: int) -> datetime:
    """datetime from Binance-timestamp"""
    return datetime.fromtimestamp(stamp / 1000).replace(tzinfo=pytz.UTC, microsecond=0)


def bstrptime(stamp: str) -> datetime:
    """datetime from Binance datetime string: e.g. `2019-10-12 11:12:02`"""
    return datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC)


def binance_history_iterator(
    fetch_function: Callable,
    period_length: int = 60,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    _depth: int = 1,
) -> Iterator:
    """
    Loop through history n days at a time, because binance API has limitations on maximum period that can be queried

    If `TooManyResultsError` is raised in `fetch_function`, period length is reduced and the method is called again,
    until the error is not raised
    """
    start_date = start_date if start_date is not None else datetime(2018, 1, 1)
    end_date = (end_date if end_date is not None else datetime.now()).replace(hour=23, minute=59, second=59)
    while start_date.date() < end_date.date():
        try:
            while True:
                try:
                    yield fetch_function(
                        startTime=to_timestamp(start_date),
                        endTime=to_timestamp(min(start_date + timedelta(days=period_length), end_date)),
                    )
                    break
                except BinanceAPIException as err:
                    if "Too much request weight used" in str(err):
                        logger.info("Too much Binance API weight used, on cooldown")
                        time.sleep(15)  # API cool down time is not accessible. Try again soon

        except TooManyResultsError:
            # Too many results returned in fetch_function so not all data may be included.
            # Try again with a smaller period
            yield from binance_history_iterator(
                fetch_function=fetch_function,
                period_length=int(period_length / 2),
                start_date=start_date,
                end_date=(min(start_date + timedelta(days=period_length) * _depth, end_date)).replace(
                    hour=23, minute=59, second=59
                ),
                _depth=_depth + 1,
            )

            # Break in order to not query the endpoint with dates that are already queried previously
            if _depth > 1:
                break

        start_date += timedelta(days=period_length)


@lru_cache
def get_binance_client() -> BinanceClient:
    client = BinanceClient(settings.BINANCE_API_KEY, settings.BINANCE_API_SECRET)
    return client


def get_binance_deposits(start_date: datetime | None = None) -> Iterator[list[dict]]:
    client = get_binance_client()
    return binance_history_iterator(client.get_deposit_history, start_date=start_date)


def get_binance_withdraws(start_date: datetime | None = None) -> Iterator[list[dict]]:
    client = get_binance_client()
    return binance_history_iterator(client.get_withdraw_history, start_date=start_date)


def get_convert_trade_history(start_date: datetime | None = None) -> Iterator[list[dict]]:
    client = get_binance_client()
    return binance_history_iterator(client.get_convert_trade_history, start_date=start_date, period_length=30)


def get_binance_dust_log() -> list:
    """
    Binance returns dust conversions only from the past ~1 year.
    To add and older dust conversions you must `Generate all statements` on the Binance website:
    https://www.binance.com/en/my/wallet/history/deposit-crypto
    Then manually import those converts using the json importer.
    You need to add `tx_id` to those transactions if converted multiple currencies in a single batch.
    """
    client = get_binance_client()
    return client.get_dust_log()["userAssetDribblets"]


def get_binance_dividends(start_date: datetime | None = None) -> Iterator[list[dict]]:
    def dividends(startTime: int, endTime: int):
        response = client.get_asset_dividend_history(startTime=startTime, endTime=endTime, limit=500)
        if response["total"] >= 500:
            raise TooManyResultsError
        return response["rows"]

    client = get_binance_client()
    return binance_history_iterator(
        dividends,
        period_length=60,  # Documented value is 90 but in reality it seems to be 60
        start_date=start_date,
    )


def get_binance_flexible_interest_history(
    start_date: datetime | None = None,
) -> Iterator[list[BinanceFlexibleInterest]]:
    def interests(startTime: int, endTime: int) -> list[BinanceFlexibleInterest]:
        output = []
        for type in ("BONUS", "REALTIME", "REWARDS"):
            response: BinanceFlexibleInterestHistoryResponse = client.get_flexible_interest_history(
                startTime=startTime,
                endTime=endTime,
                size=100,
                type=type,
            )
            if response["total"] >= 100:
                raise TooManyResultsError
            if response["total"] == 0:
                continue

            rows: list[BinanceFlexibleInterest] = response["rows"]
            output.extend(rows)
        return output

    client = get_binance_client()
    out = binance_history_iterator(interests, period_length=30, start_date=start_date)
    return out


def get_binance_locked_interest_history(start_date: datetime | None = None) -> Iterator[list[BinanceLockedInterest]]:
    def interests(startTime: int, endTime: int) -> list[BinanceLockedInterest]:
        output = []
        response: BinanceLockedInterestHistoryResponse = client.get_locked_interest_history(
            startTime=startTime,
            endTime=endTime,
            size=100,
        )
        if response["total"] >= 100:
            raise TooManyResultsError
        if response["total"] == 0:
            return []

        rows: list[BinanceLockedInterest] = response["rows"]
        output.extend(rows)
        return output

    client = get_binance_client()
    out = binance_history_iterator(interests, period_length=30, start_date=start_date)
    return out


def get_binance_beth_interest_history(start_date: datetime | None = None) -> Iterator[list[BinanceLockedInterest]]:
    def interests(startTime: int, endTime: int) -> list[BinanceLockedInterest]:
        output = []
        response: BinanceLockedInterestHistoryResponse = client.get_beth_interest_history(
            startTime=startTime,
            endTime=endTime,
            size=100,
        )
        if response["total"] >= 100:
            raise TooManyResultsError
        if response["total"] == 0:
            return []

        rows: list[BinanceLockedInterest] = response["rows"]
        output.extend(rows)
        return output

    client = get_binance_client()
    out = binance_history_iterator(interests, period_length=30, start_date=start_date)
    return out
