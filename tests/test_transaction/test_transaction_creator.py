from decimal import Decimal

import pytest
from django.utils import timezone

from crypto_fifo_taxes.enums import TransactionType
from crypto_fifo_taxes.models import Transaction, TransactionDetail
from crypto_fifo_taxes.utils.currency import get_fiat_currency
from crypto_fifo_taxes.utils.transaction_creator import TransactionCreator
from tests.factories import CryptoCurrencyFactory, WalletFactory


@pytest.mark.django_db()
def test_transaction_creator():
    wallet = WalletFactory.create()
    fiat = get_fiat_currency()
    crypto = CryptoCurrencyFactory.create(symbol="BTC")

    # Deposit
    TransactionCreator(timestamp=timezone.now()).create_deposit(wallet=wallet, currency=fiat, quantity=500)

    # Withdrawal
    TransactionCreator(timestamp=timezone.now()).create_withdrawal(wallet=wallet, currency=fiat, quantity=200)
    assert Transaction.objects.count() == 2
    assert TransactionDetail.objects.count() == 2

    # Trade
    tx_creator = TransactionCreator(timestamp=timezone.now())
    tx_creator.add_from_detail(wallet=wallet, currency=fiat, quantity=200)
    tx_creator.add_to_detail(wallet=wallet, currency=crypto, quantity=2)
    tx_creator.add_fee_detail(wallet=wallet, currency=crypto, quantity=Decimal("0.0001"))
    tx = tx_creator.create_trade()

    assert Transaction.objects.count() == 3
    assert TransactionDetail.objects.count() == 5
    assert tx.transaction_type == TransactionType.TRADE

    # Trade using create_transaction
    tx_creator = TransactionCreator(timestamp=timezone.now(), type=TransactionType.TRADE)
    tx_creator.add_from_detail(wallet=wallet, currency=fiat, quantity=200)
    tx_creator.add_to_detail(wallet=wallet, currency=crypto, quantity=2)
    tx_creator.add_fee_detail(wallet=wallet, currency=crypto, quantity=Decimal("0.0001"))
    tx = tx_creator.create_transaction()

    assert Transaction.objects.count() == 4
    assert TransactionDetail.objects.count() == 8
    assert tx.transaction_type == TransactionType.TRADE
