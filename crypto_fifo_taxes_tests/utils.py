from datetime import datetime, timedelta
from typing import Union

import pytz

from crypto_fifo_taxes.models import Currency
from crypto_fifo_taxes.utils.transaction_creator import TransactionCreator
from crypto_fifo_taxes_tests.factories import CryptoCurrencyFactory, FiatCurrencyFactory, TransactionDetailFactory


def _set_timezone(timestamp):
    """Set UTC timezone to a datetime object"""
    if timestamp is not None:
        return timestamp.replace(tzinfo=pytz.UTC)


class TxTime:
    """Util to generate sequential timestamps for sequential transactions"""

    def __init__(self, timestamp=None, increment=None):
        timestamp = _set_timezone(timestamp)
        self.timestamp = timestamp if timestamp is not None else datetime(2010, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)
        self.increment = increment if increment is not None else {"minutes": 1}

    def next(self):
        self.timestamp = self.timestamp + timedelta(**self.increment)
        return self.timestamp

    def next_day(self):
        """Set timestamp to next day, reset hours and minutes"""
        next_day = {"days": 1, "hours": -self.timestamp.hour, "minutes": -self.timestamp.minute}
        self.timestamp = self.timestamp + timedelta(**next_day)
        return self.timestamp


class WalletHelper:
    """
    Wallet testing utility.
    Used to help create simple deposits, withdrawals and trades within a single wallet.

    Simpler to use than TransactionCreator, due to remembering the wallet object,
    also accepting currency as a string and not requiring timestamp to create a transaction

    By default, new transactions created using WalletHelper are spaced 1 minute from the previous one
    """

    def __init__(self, wallet, start_time=None):
        self.wallet = wallet
        self.tx_time = TxTime(start_time)

    def deposit(self, currency, quantity, timestamp=None):
        tx_creator = TransactionCreator()
        tx_creator.to_detail = TransactionDetailFactory.build(wallet=self.wallet, currency=currency, quantity=quantity)
        return tx_creator.create_deposit(timestamp=_set_timezone(timestamp) or self.tx_time.next())

    def withdraw(self, currency, quantity, timestamp=None):
        tx_creator = TransactionCreator()
        tx_creator.from_detail = TransactionDetailFactory.build(
            wallet=self.wallet, currency=currency, quantity=quantity
        )
        return tx_creator.create_withdrawal(timestamp=_set_timezone(timestamp) or self.tx_time.next())

    def trade(self, from_currency, from_currency_quantity, to_currency, to_currency_quantity, timestamp=None):
        tx_creator = TransactionCreator()
        tx_creator.from_detail = TransactionDetailFactory.build(
            wallet=self.wallet, currency=from_currency, quantity=from_currency_quantity
        )
        tx_creator.to_detail = TransactionDetailFactory.build(
            wallet=self.wallet, currency=to_currency, quantity=to_currency_quantity
        )
        return tx_creator.create_trade(timestamp=_set_timezone(timestamp) or self.tx_time.next())


def get_currency(currency: Union[Currency, str], is_fiat: bool = False):
    """Allow passing currency as a string, instead of a Currency object."""
    currency_factory = CryptoCurrencyFactory if not is_fiat else FiatCurrencyFactory
    if isinstance(currency, str):
        currency = currency_factory.create(symbol=currency)
    return currency
