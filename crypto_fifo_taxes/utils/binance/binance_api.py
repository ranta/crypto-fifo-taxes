from datetime import datetime, timedelta
from functools import lru_cache
from typing import Callable, Iterator

import pytz
from django.conf import settings

from crypto_fifo_taxes.exceptions import TooManyResultsError
from crypto_fifo_taxes.utils.binance.binance_client import BinanceClient


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
    start_date: datetime = None,
    end_date: datetime = None,
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
            yield fetch_function(
                startTime=to_timestamp(start_date),
                endTime=to_timestamp(min(start_date + timedelta(days=period_length), end_date)),
            )
        except TooManyResultsError:
            # Too many results returned in fetch_function so not all data may be included.
            # Try again with a smaller period
            for result in binance_history_iterator(
                fetch_function=fetch_function,
                period_length=int(period_length / 2),
                start_date=start_date,
                end_date=(min(start_date + timedelta(days=period_length) * _depth, end_date)).replace(
                    hour=23, minute=59, second=59
                ),
                _depth=_depth + 1,
            ):
                # Yield results separately instead of together in a single iterable to keep output as the same
                yield result

            # Break in order to not query the endpoint with dates that are already queried previously
            if _depth > 1:
                break

        start_date += timedelta(days=period_length)


@lru_cache()
def get_binance_client() -> BinanceClient:
    client = BinanceClient(settings.BINANCE_API_KEY, settings.BINANCE_API_SECRET)
    return client


def get_binance_deposits(start_date: datetime = None) -> Iterator[list[dict]]:
    client = get_binance_client()
    return binance_history_iterator(client.get_deposit_history, start_date=start_date)


def get_binance_withdraws(start_date: datetime = None) -> Iterator[list[dict]]:
    client = get_binance_client()
    return binance_history_iterator(client.get_withdraw_history, start_date=start_date)


def get_binance_dust_log() -> list:
    client = get_binance_client()
    return client.get_dust_log()["userAssetDribblets"]


def get_binance_dividends(start_date: datetime = None) -> Iterator[list[dict]]:
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


def get_binance_interest_history(start_date: datetime = None) -> Iterator[list[dict]]:
    def interests(startTime: int, endTime: int) -> list:
        """This endpoint can be paginated, so do that as it's more efficient than reducing period length"""
        output = []
        for type in ("DAILY", "ACTIVITY", "CUSTOMIZED_FIXED"):
            page = 1
            while True:
                interest_history = client.get_lending_interest_history(
                    startTime=startTime,
                    endTime=endTime,
                    size=100,
                    lendingType=type,
                    current=page,
                )
                output += interest_history
                if len(interest_history) < 100:
                    break
                page += 1
        return output

    client = get_binance_client()
    return binance_history_iterator(interests, period_length=30, start_date=start_date)
