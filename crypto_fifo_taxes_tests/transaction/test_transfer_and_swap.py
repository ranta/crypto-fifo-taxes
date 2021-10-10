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

    now = timezone.now()
    # Add some BTC to wallet
    wallet_helper = WalletHelper(wallet_from)
    wallet_helper.deposit(fiat, 1000)
    wallet_helper.trade(fiat, 1000, btc, 10)

    tx_creator = TransactionCreator(timestamp=now)
    tx_creator.add_from_detail(wallet=wallet_from, currency=btc, quantity=10)
    tx_creator.add_to_detail(wallet=wallet_to, currency=btc, quantity=10)
    tx_creator.add_fee_detail(wallet=wallet_to, currency=btc, quantity=1)
    tx = tx_creator.create_transfer()

    assert tx.transaction_type == TransactionType.TRANSFER
    assert tx.from_detail.cost_basis == tx.to_detail.cost_basis
    assert wallet_from.get_current_balance("BTC") == Decimal(0)
    assert wallet_to.get_current_balance("BTC") == Decimal(9)
    assert wallet_to.get_consumable_currency_balances(btc, now)[-1].quantity_left == Decimal(9)


@pytest.mark.django_db
def test_swap():
    fiat = FiatCurrencyFactory.create(symbol="EUR")
    ven = CryptoCurrencyFactory.create(symbol="VEN")
    vet = CryptoCurrencyFactory.create(symbol="VET")
    btc = CryptoCurrencyFactory.create(symbol="BTC")

    wallet = WalletFactory.create(fiat=fiat)

    # Add some BTC to wallet
    wallet_helper = WalletHelper(wallet)
    wallet_helper.deposit(fiat, 2000)
    wallet_helper.trade(fiat, 1000, ven, 1000)
    wallet_helper.swap(ven, 1000, vet, 100000)

    tx = wallet.transaction_details.last().transaction
    assert tx.transaction_type == TransactionType.SWAP
    assert tx.from_detail.cost_basis == tx.to_detail.cost_basis
    assert wallet.get_current_balance("VEN") == Decimal(0)
    assert wallet.get_current_balance("VET") == Decimal(100000)

    # 1:10 Redenomination
    wallet_helper.trade(fiat, 1000, btc, 10)
    wallet_helper.swap(from_currency=btc, from_currency_quantity=10, to_currency=btc, to_currency_quantity=100)
    balances = wallet.get_current_balance()
    assert balances["BTC"] == 100


# TODO: Test using FIFO to make sure original cost_basis is kept for every single coin
