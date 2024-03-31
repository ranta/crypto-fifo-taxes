from datetime import UTC, datetime, timedelta
from decimal import Decimal

from crypto_fifo_taxes.models import Currency, Wallet
from crypto_fifo_taxes.utils.currency import get_fiat_currency
from crypto_fifo_taxes.utils.transaction_creator import TransactionCreator
from tests.factories import CryptoCurrencyFactory, CurrencyPriceFactory, TransactionDetailFactory, WalletFactory


def _set_timezone(timestamp) -> datetime | None:
    """Set UTC timezone to a datetime object"""
    if timestamp is not None:
        return timestamp.replace(tzinfo=UTC)
    return None


class TxTime:
    """Util to generate sequential timestamps for sequential transactions"""

    def __init__(self, timestamp=None, increment: None | timedelta = None):
        if timestamp is not None:
            self.timestamp = _set_timezone(timestamp)
        else:
            self.timestamp = datetime(2010, 1, 1, 12, 0, 0, tzinfo=UTC)
        self.increment = increment if increment is not None else timedelta(minutes=1)

    def next(self) -> datetime:
        """Get next timestamp, incrementing by the set increment"""
        self.timestamp = self.timestamp + self.increment
        return self.timestamp

    def next_day(self) -> None:
        """Set timestamp to next day, reset hours and minutes"""
        self.timestamp = self.timestamp + timedelta(days=1, hours=-self.timestamp.hour, minutes=-self.timestamp.minute)

    @property
    def date(self) -> datetime.date:
        return self.timestamp.date()


class WalletHelper:
    """
    Wallet testing utility.
    Used to help create simple deposits, withdrawals and trades within a single wallet.

    Simpler to use than TransactionCreator, due to remembering the wallet object,
    also accepting currency as a string and not requiring timestamp to create a transaction

    By default, new transactions created using WalletHelper are spaced 1 minute from the previous one
    """

    def __init__(
        self,
        wallet: Wallet | None = None,
        start_time: datetime | None = None,
        increment: timedelta | None = None,
        auto_create_prices: bool = True,
    ):
        self.wallet = wallet if wallet is not None else self._get_wallet()
        self.tx_time = TxTime(start_time, increment)
        self.auto_create_prices = auto_create_prices

    @property
    def date(self) -> datetime.date:
        return self.tx_time.date

    def _get_wallet(self) -> Wallet:
        wallets_count = Wallet.objects.count()
        if wallets_count == 1:
            return Wallet.objects.first()
        elif wallets_count == 0:
            return WalletFactory.create(name="default")
        else:
            raise ValueError("Multiple wallets exist, please specify the wallet.")

    def deposit(self, currency: Currency | str, quantity: Decimal | int, timestamp: datetime | None = None):
        tx_timestamp = _set_timezone(timestamp) or self.tx_time.next()
        tx_creator = TransactionCreator(timestamp=tx_timestamp, fill_cost_basis=True)
        tx_creator.to_detail = TransactionDetailFactory.build(wallet=self.wallet, currency=currency, quantity=quantity)

        if self.auto_create_prices:
            CurrencyPriceFactory.create(currency=currency, date=self.date, price=quantity)

        return tx_creator.create_deposit()

    def withdraw(self, currency: Currency | str, quantity: Decimal | int, timestamp: datetime | None = None):
        tx_timestamp = _set_timezone(timestamp) or self.tx_time.next()
        tx_creator = TransactionCreator(timestamp=tx_timestamp, fill_cost_basis=True)
        tx_creator.from_detail = TransactionDetailFactory.build(
            wallet=self.wallet, currency=currency, quantity=quantity
        )

        if self.auto_create_prices:
            CurrencyPriceFactory.create(currency=currency, date=self.date, price=quantity)

        return tx_creator.create_withdrawal()

    def _get_tx_creator(
        self,
        from_currency: Currency | str,
        from_currency_quantity: Decimal | int,
        to_currency: Currency | str,
        to_currency_quantity: Decimal | int,
        fee_currency: Currency | str | None = None,
        fee_currency_quantity: Decimal | int | None = None,
        timestamp: datetime | None = None,
    ):
        tx_creator = TransactionCreator(timestamp=_set_timezone(timestamp) or self.tx_time.next(), fill_cost_basis=True)
        tx_creator.from_detail = TransactionDetailFactory.build(
            wallet=self.wallet, currency=from_currency, quantity=from_currency_quantity
        )
        tx_creator.to_detail = TransactionDetailFactory.build(
            wallet=self.wallet, currency=to_currency, quantity=to_currency_quantity
        )
        if fee_currency is not None and fee_currency_quantity is not None:
            tx_creator.fee_detail = TransactionDetailFactory.build(
                wallet=self.wallet, currency=fee_currency, quantity=fee_currency_quantity
            )

        if self.auto_create_prices:
            CurrencyPriceFactory.create(currency=from_currency, date=self.date, price=from_currency_quantity)
            to_price = from_currency_quantity / to_currency_quantity
            CurrencyPriceFactory.create(currency=to_currency, date=self.date, price=to_price)

        return tx_creator

    def trade(
        self,
        from_currency: Currency | str,
        from_currency_quantity: Decimal | int,
        to_currency: Currency | str,
        to_currency_quantity: Decimal | int,
        fee_currency: Currency | str | None = None,
        fee_currency_quantity: Decimal | int | None = None,
        timestamp=None,
    ):
        tx_creator = self._get_tx_creator(
            from_currency,
            from_currency_quantity,
            to_currency,
            to_currency_quantity,
            fee_currency,
            fee_currency_quantity,
            timestamp,
        )
        return tx_creator.create_trade()

    def swap(
        self,
        from_currency: Currency | str,
        from_currency_quantity: Decimal | int,
        to_currency: Currency | str,
        to_currency_quantity: Decimal | int,
        fee_currency: Currency | str | None = None,
        fee_currency_quantity: Decimal | int | None = None,
        timestamp=None,
    ):
        tx_creator = self._get_tx_creator(
            from_currency,
            from_currency_quantity,
            to_currency,
            to_currency_quantity,
            fee_currency,
            fee_currency_quantity,
            timestamp,
        )
        return tx_creator.create_swap()


def get_test_currency(currency: Currency | str, is_fiat: bool = False):
    """Allow passing currency as a string, instead of a Currency object."""
    if is_fiat:
        return get_fiat_currency()
    elif isinstance(currency, str):
        return CryptoCurrencyFactory.create(symbol=currency)
    return currency
