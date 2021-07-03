from decimal import Decimal

import pytest

from crypto_fifo_taxes_tests.factories import CryptoCurrencyFactory, FiatCurrencyFactory, WalletFactory
from crypto_fifo_taxes_tests.utils import WalletHelper


@pytest.mark.django_db
def test_cost_basis_simple_fiat_trades_cost_basis():
    wallet = WalletFactory.create()
    wallet_helper = WalletHelper(wallet)

    crypto = CryptoCurrencyFactory.create(symbol="BTC")
    fiat = FiatCurrencyFactory.create(symbol="EUR")

    # Deposit FIAT to wallet
    wallet_helper.deposit(fiat, 1000)

    # Buy 10 BTC with 1000 EUR
    tx = wallet_helper.trade(fiat, 1000, crypto, 10)
    assert tx.to_detail.cost_basis == Decimal(100)  # 1 BTC == 100 EUR

    # Sell 5 BTC for 1000 EUR
    tx = wallet_helper.trade(crypto, 5, fiat, 1000)
    assert tx.to_detail.cost_basis == Decimal(200)  # 1 BTC == 200 EUR

    # Sell 5 BTC for 2000 EUR
    tx = wallet_helper.trade(crypto, 5, fiat, 2000)
    assert tx.to_detail.cost_basis == Decimal(400)  # 1 BTC == 400 EUR


