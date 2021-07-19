from decimal import Decimal

import pytest
from django.utils import timezone

from crypto_fifo_taxes.enums import TransactionType
from crypto_fifo_taxes.utils.transaction_creator import TransactionCreator
from crypto_fifo_taxes_tests.factories import CryptoCurrencyFactory, FiatCurrencyFactory, WalletFactory
from crypto_fifo_taxes_tests.utils import WalletHelper


@pytest.mark.django_db
def test_transfer():
    fiat = FiatCurrencyFactory.create(symbol="EUR")
    btc = CryptoCurrencyFactory.create(symbol="BTC")

    wallet_from = WalletFactory.create(fiat=fiat)
    wallet_to = WalletFactory.create(fiat=fiat)

    # Add some BTC to wallet
    wallet_helper = WalletHelper(wallet_from)
    wallet_helper.deposit(fiat, 1000)
    wallet_helper.trade(fiat, 1000, btc, 10)

    tx_creator = TransactionCreator()
    tx_creator.add_from_detail(wallet=wallet_from, currency=btc, quantity=10)
    tx_creator.add_to_detail(wallet=wallet_to, currency=btc, quantity=10)
    tx = tx_creator.create_transfer(timestamp=timezone.now())

    assert tx.transaction_type == TransactionType.TRANSFER
    assert tx.from_detail.cost_basis == tx.to_detail.cost_basis
    assert wallet_from.get_current_balance("BTC") == Decimal(0)
    assert wallet_to.get_current_balance("BTC") == Decimal(10)


@pytest.mark.django_db
def test_swap():
    fiat = FiatCurrencyFactory.create(symbol="EUR")
    ven = CryptoCurrencyFactory.create(symbol="VEN")
    vet = CryptoCurrencyFactory.create(symbol="VET")

    wallet = WalletFactory.create(fiat=fiat)

    # Add some BTC to wallet
    wallet_helper = WalletHelper(wallet)
    wallet_helper.deposit(fiat, 1000)
    wallet_helper.trade(fiat, 1000, ven, 1000)
    wallet_helper.swap(ven, 1000, vet, 100000)

    tx = wallet.transaction_details.last().transaction
    assert tx.transaction_type == TransactionType.SWAP
    assert tx.from_detail.cost_basis == tx.to_detail.cost_basis
    assert wallet.get_current_balance("VEN") == Decimal(0)
    assert wallet.get_current_balance("VET") == Decimal(100000)


# TODO: Test using FIFO to make sure original cost_basis is kept for every single coin
