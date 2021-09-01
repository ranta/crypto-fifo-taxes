from collections import namedtuple
from datetime import datetime, timedelta
from decimal import Decimal
from functools import lru_cache
from typing import Iterator

import pytz
from django.conf import settings

from crypto_fifo_taxes.models import Wallet
from crypto_fifo_taxes.utils.binance.binance_client import BinanceClient

Interval = namedtuple("Interval", "startTime endTime")


def to_timestamp(dt: datetime) -> int:
    """datetime to Binance-timestamp"""
    return int(datetime.timestamp(dt)) * 1000


def from_timestamp(stamp: int) -> datetime:
    """datetime from Binance-timestamp"""
    return datetime.fromtimestamp(stamp / 1000).replace(tzinfo=pytz.UTC, microsecond=0)


def bstrptime(stamp: str) -> datetime:
    """datetime from Binance datetime string: e.g. `2019-10-12 11:12:02`"""
    return datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC)


def iterate_history(start_date=datetime(2017, 1, 1), delta_days: int = 90) -> "Interval":
    """
    Binance allows fetching from the trade history at most 90 days at a time
    This function makes it easier to get all required intervals
    """
    while start_date + timedelta(days=delta_days) < datetime.now():
        start_date = start_date + timedelta(days=delta_days)
        yield Interval(
            to_timestamp(start_date),
            to_timestamp(
                min(start_date + timedelta(days=delta_days), datetime.now().replace(hour=23, minute=59, second=59))
            ),
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


def get_binance_interest_history() -> Iterator[list[dict]]:
    client = get_binance_client()
    for type in ("DAILY", "ACTIVITY", "CUSTOMIZED_FIXED"):
        for interval in iterate_history(delta_days=30):
            interest_history = client.get_lending_interest_history(
                startTime=interval.startTime, endTime=interval.endTime, size=100, lendingType=type
            )
            if len(interest_history) == 100:
                # Too many interests returned in timeframe, try to retrieve interests in two parts
                for delta_split in range(0, 2):
                    interest_history = client.get_lending_interest_history(
                        startTime=to_timestamp(from_timestamp(interval.startTime) + timedelta(days=15) * delta_split),
                        endTime=to_timestamp(from_timestamp(interval.endTime) + timedelta(days=15) * (delta_split - 1)),
                        size=100,
                        lendingType=type,
                    )
                    assert len(interest_history) != 100
                    yield interest_history
            yield interest_history


def get_binance_wallet_balance() -> dict[str:Decimal]:
    def filter_spot_balances(row):
        if row["asset"] in settings.IGNORED_TOKENS:
            return False
        if len(row["asset"]) >= 5 and row["asset"].startswith("LD"):
            # Lending asset
            return False
        return Decimal(row["free"]) > 0 or Decimal(row["locked"]) > 0

    def filter_savings_balances(row):
        return Decimal(row["totalAmount"]) > 0

    client = get_binance_client()

    # Get positive balances from binance SPOT and SAVINGS accounts
    spot_wallet = filter(filter_spot_balances, client.get_account()["balances"])
    savings_wallet = filter(filter_savings_balances, client.get_lending_position())

    # Combine balances
    balances = {}
    for row in spot_wallet:
        balances[row["asset"]] = Decimal(row["free"]) + Decimal(row["locked"])
    for row in savings_wallet:
        if row["asset"] in balances.keys():
            balances[row["asset"]] = balances["asset"] + Decimal(row["totalAmount"])
        else:
            balances[row["asset"]] = Decimal(row["totalAmount"])
    for symbol, quantity in settings.LOCKED_STAKING.items():
        if symbol in balances.keys():
            balances[symbol] = balances[symbol] + quantity
        else:
            balances[symbol] = quantity

    # Remove zero balances
    balance_diff = {}
    for symbol, quantity in balances.items():
        if quantity != Decimal(0):
            balance_diff[symbol] = quantity

    return balance_diff


def get_binance_wallet_differences() -> dict[str, Decimal]:
    """
    Return the balance differences of tokens of:
    `Binance live wallet balance` - `local calculated wallet balance`

    Positive balance = Deposit transactions are missing, local wallet is missing funds that are in Binance Wallet
    Negative balance = Too much withdrawal transactions, again most likely deposits are missing 😅
    """
    live_wallet = get_binance_wallet_balance()
    local_wallet = Wallet.objects.get(name="Binance").get_current_balance()

    for symbol, quantity in local_wallet.items():
        if symbol in live_wallet:
            live_wallet[symbol] = live_wallet[symbol] - quantity
        else:
            live_wallet[symbol] = -quantity

    # Remove zero balances
    balance_diff = {}
    for symbol, quantity in live_wallet.items():
        if quantity != Decimal(0):
            balance_diff[symbol] = quantity

    return balance_diff
