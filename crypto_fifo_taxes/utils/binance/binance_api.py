from collections import namedtuple
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Iterator

import pytz
from django.conf import settings

from crypto_fifo_taxes.utils.binance.binance_client import BinanceClient

Interval = namedtuple("Interval", "startTime endTime")


def to_timestamp(dt: datetime) -> int:
    """datetime to Binance-timestamp"""
    return int(datetime.timestamp(dt)) * 1000


def from_timestamp(stamp: int) -> datetime:
    """datetime from Binance-timestamp"""
    return datetime.fromtimestamp(stamp / 1000).replace(tzinfo=pytz.UTC)


def bstrptime(stamp: str) -> datetime:
    """datetime from Binance datetime string: e.g. `2019-10-12 11:12:02`"""
    return datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC)


def iterate_history(start_date=datetime(2017, 1, 1), delta_days: int = 90) -> "Interval":
    """
    Binance allows fetching from the trade history at most 90 days at a time
    This function makes it easier to get all required intervals
    """
    while start_date < datetime.now():
        start_date = start_date + timedelta(days=delta_days)
        yield Interval(
            to_timestamp(start_date),
            to_timestamp(start_date + timedelta(days=delta_days)),
        )


@lru_cache()
def get_binance_client() -> BinanceClient:
    client = BinanceClient(settings.BINANCE_API_KEY, settings.BINANCE_API_SECRET)
    return client


def get_binance_deposits() -> Iterator[list[dict]]:
    client = get_binance_client()
    for interval in iterate_history():
        yield client.get_deposit_history(startTime=interval.startTime, endTime=interval.endTime)


def get_binance_withdraws() -> Iterator[list[dict]]:
    client = get_binance_client()
    for interval in iterate_history():
        yield client.get_withdraw_history(startTime=interval.startTime, endTime=interval.endTime)


def get_binance_dust_log() -> list:
    client = get_binance_client()
    return client.get_dust_log()["userAssetDribblets"]


def get_binance_dividends() -> Iterator[list[dict]]:
    client = get_binance_client()
    for interval in iterate_history():
        dividends = client.get_asset_dividend_history(startTime=interval.startTime, endTime=interval.endTime, limit=500)

        # If batch contains 500 transactions, some data is most likely left out, most likely Interval should be shorter.
        assert dividends["total"] < 500, "Dividend batch size limit reached, not all data may be included"
        yield dividends["rows"]
