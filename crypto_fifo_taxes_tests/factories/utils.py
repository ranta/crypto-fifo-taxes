from typing import Union

from django.utils import timezone

from crypto_fifo_taxes.models import Currency
from crypto_fifo_taxes.utils.transaction_creator import TransactionCreator
from crypto_fifo_taxes_tests.factories import CryptoCurrencyFactory, FiatCurrencyFactory, TransactionDetailFactory


class WalletHelper:
    """
    Wallet testing utility.
    Used to help create simple deposits and withdrawals within a single wallet.

    Simpler to use than TransactionCreator, due to saving wallet object,
    also accepting currency as a string and not requiring timestamp to create a transaction
    """

    def __init__(self, wallet):
        self.wallet = wallet

    def deposit(self, currency, quantity, timestamp=None):
        tx_creator = TransactionCreator()
        tx_creator.to_detail = TransactionDetailFactory.build(wallet=self.wallet, currency=currency, quantity=quantity)
        return tx_creator.create_deposit(timestamp=timestamp or timezone.now())

    def withdraw(self, currency, quantity, timestamp=None):
        tx_creator = TransactionCreator()
        tx_creator.from_detail = TransactionDetailFactory.build(
            wallet=self.wallet, currency=currency, quantity=quantity
        )
        return tx_creator.create_withdrawal(timestamp=timestamp or timezone.now())

    def _trade(self, currency_1, quantity_1, currency_2, quantity_2, timestamp=None):
        tx_creator = TransactionCreator()
        tx_creator.from_detail = TransactionDetailFactory.build(
            wallet=self.wallet, currency=currency_1, quantity=quantity_1
        )
        tx_creator.to_detail = TransactionDetailFactory.build(
            wallet=self.wallet, currency=currency_2, quantity=quantity_2
        )
        return tx_creator.create_trade(timestamp=timestamp or timezone.now())

    def buy_crypto(self, crypto, crypto_quantity, fiat, fiat_quantity, timestamp=None):
        return self._trade(
            currency_1=fiat,
            quantity_1=fiat_quantity,
            currency_2=crypto,
            quantity_2=crypto_quantity,
            timestamp=timestamp,
        )

    def sell_crypto(self, crypto, crypto_quantity, fiat, fiat_quantity, timestamp=None):
        return self._trade(
            currency_1=crypto,
            quantity_1=crypto_quantity,
            currency_2=fiat,
            quantity_2=fiat_quantity,
            timestamp=timestamp,
        )


def get_currency(currency: Union[Currency, str], is_fiat: bool = False):
    """Allow passing currency as a string, instead of a Currency object."""
    currency_factory = CryptoCurrencyFactory if not is_fiat else FiatCurrencyFactory
    if isinstance(currency, str):
        currency = currency_factory.create(symbol=currency)
    return currency
