from collections import namedtuple
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Iterator

import pytz
from binance.client import Client
from django.conf import settings

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


def iterate_history(start_date=datetime(2017, 1, 1)) -> "Interval":
    """
    Binance allows fetching from the history at most 90 days at a time
    This function makes it easier to get all required intervals
    """
    i = 0
    while start_date < datetime.now():
        start_date = start_date + timedelta(days=90)
        yield Interval(
            to_timestamp(start_date),
            to_timestamp(start_date + timedelta(days=90)),
        )
        i += 1


@lru_cache()
def get_binance_client() -> Client:
    client = Client(settings.BINANCE_API_KEY, settings.BINANCE_API_SECRET)
    return client


def get_binance_deposits() -> Iterator[list[dict]]:
    client = get_binance_client()
    for interval in iterate_history():
        yield client.get_deposit_history(startTime=interval.startTime, endTime=interval.endTime)


def get_binance_withdraws() -> Iterator[list[dict]]:
    client = get_binance_client()
    for interval in iterate_history():
        yield client.get_withdraw_history(startTime=interval.startTime, endTime=interval.endTime)
