from decimal import Decimal

import pytest

from crypto_fifo_taxes.models import Currency
from crypto_fifo_taxes_tests.factories import TransactionDetailFactory, TransactionFactory, WalletFactory
from crypto_fifo_taxes_tests.factories.utils import WalletHelper


@pytest.mark.django_db
def test_wallet_get_used_currency_ids():
    wallet = WalletFactory.create()

    # Create deposits
    TransactionFactory.create(to_detail=TransactionDetailFactory.create(wallet=wallet, currency="BTC"))
    for i in range(0, 9):
        TransactionFactory.create(to_detail=TransactionDetailFactory.create(wallet=wallet))

    currencies = wallet.get_used_currency_ids()
    assert len(currencies) == 10
    assert Currency.objects.last().pk in currencies
    assert Currency.objects.get(symbol="BTC").pk in currencies


@pytest.mark.django_db
def test_wallet_get_balance_deposit_and_withdrawal_single_currency():
    wallet = WalletFactory.create()

    wallet_helper = WalletHelper(wallet)

    # Create deposits
    wallet_helper.deposit(currency="BTC", quantity=5)
    wallet_helper.deposit(currency="BTC", quantity=10)
    wallet_helper.withdraw(currency="BTC", quantity=2.5)

    currencies = wallet.get_balance()
    assert currencies.count() == 1
    assert currencies.first().symbol == "BTC"
    assert currencies.first().deposits == Decimal(15)
    assert currencies.first().withdrawals == Decimal(2.5)
    assert currencies.first().balance == Decimal(12.5)
