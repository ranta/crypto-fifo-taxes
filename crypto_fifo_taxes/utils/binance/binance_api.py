from datetime import datetime, timedelta
from decimal import Decimal
from functools import lru_cache
from typing import Callable, Iterator

import pytz
from django.conf import settings

from crypto_fifo_taxes.exceptions import TooManyResultsError
from crypto_fifo_taxes.models import Wallet
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
    start_date: datetime = datetime(2018, 1, 1),
    end_date: datetime = None,
):
    """
    Loop through history n days at a time, because binance API has limitations on maximum period that can be queried
    """
    end_date = (end_date if end_date is not None else datetime.now()).replace(hour=23, minute=59, second=59)
    while start_date + timedelta(days=period_length) < end_date:
        try:
            yield fetch_function(
                startTime=to_timestamp(start_date),
                endTime=to_timestamp(min(start_date + timedelta(days=period_length), end_date)),
            )
        except TooManyResultsError:
            # Too many results returned in fetch_function so not all data may be included.
            # Try again with a smaller period
            for result in binance_history_iterator(fetch_function, int(period_length / 2), start_date, end_date):
                # yield results separately instead together in a single iterable to keep output as the same
                yield result
        start_date += timedelta(days=period_length)


@lru_cache()
def get_binance_client() -> BinanceClient:
    client = BinanceClient(settings.BINANCE_API_KEY, settings.BINANCE_API_SECRET)
    return client


def get_binance_deposits() -> Iterator[list[dict]]:
    client = get_binance_client()
    return binance_history_iterator(client.get_deposit_history)


def get_binance_withdraws() -> Iterator[list[dict]]:
    client = get_binance_client()
    return binance_history_iterator(client.get_withdraw_history)


def get_binance_dust_log() -> list:
    client = get_binance_client()
    return client.get_dust_log()["userAssetDribblets"]


def get_binance_dividends() -> Iterator[list[dict]]:
    def dividends(startTime: int, endTime: int):
        response = client.get_asset_dividend_history(startTime=startTime, endTime=endTime, limit=500)
        if response["total"] >= 500:
            raise TooManyResultsError
        return response["rows"]

    client = get_binance_client()
    return binance_history_iterator(
        dividends,
        period_length=60,  # Documented value is 90 but in reality it seems to be 60
    )


def get_binance_interest_history() -> Iterator[list[dict]]:
    def interests(startTime: int, endTime: int):
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
    return binance_history_iterator(interests, period_length=30)


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
            balances[row["asset"]] = balances[row["asset"]] + Decimal(row["totalAmount"])
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
