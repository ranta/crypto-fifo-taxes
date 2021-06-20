from decimal import Decimal

import pytest
from django.utils import timezone

from crypto_fifo_taxes.models import Transaction, TransactionDetail
from crypto_fifo_taxes.utils.transaction_creator import TransactionCreator
from crypto_fifo_taxes_tests.factories import CryptoCurrencyFactory, FiatCurrencyFactory, WalletFactory


@pytest.mark.django_db
def test_transaction_creator():
    wallet = WalletFactory.create()
    fiat = FiatCurrencyFactory.create(symbol="EUR")
    crypto = CryptoCurrencyFactory.create(symbol="BTC")

    # Deposit
    TransactionCreator().create_deposit(
        timestamp=timezone.now(), description="Deposit", wallet=wallet, currency=fiat, quantity=500
    )

    # Withdrawal
    TransactionCreator().create_withdrawal(
        timestamp=timezone.now(), description="Withdrawal", wallet=wallet, currency=fiat, quantity=200
    )

    # Trade
    tx_trade = TransactionCreator()
    tx_trade.add_from_detail(wallet=wallet, currency=fiat, quantity=200)
    tx_trade.add_to_detail(wallet=wallet, currency=crypto, quantity=2)
    tx_trade.add_fee_detail(wallet=wallet, currency=crypto, quantity=Decimal("0.0001"))
    tx_trade.create_trade(timezone.now())

    assert Transaction.objects.count() == 3
    assert TransactionDetail.objects.count() == 5
