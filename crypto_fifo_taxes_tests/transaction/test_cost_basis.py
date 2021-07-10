from decimal import Decimal

import pytest

from crypto_fifo_taxes_tests.factories import CryptoCurrencyFactory, FiatCurrencyFactory, WalletFactory
from crypto_fifo_taxes_tests.utils import WalletHelper


@pytest.mark.django_db
def test_cost_basis_fiat_crypto_fiat_trades_simple():
    """Test calculating cost basis for FIAT -> CRYPTO -> FIAT trades that don't require using FIFO"""
    wallet = WalletFactory.create()
    wallet_helper = WalletHelper(wallet)

    fiat = FiatCurrencyFactory.create(symbol="EUR")
    crypto = CryptoCurrencyFactory.create(symbol="BTC")

    # Deposit FIAT to wallet
    wallet_helper.deposit(fiat, 1000)

    # Buy 10 BTC with 1000 EUR
    tx = wallet_helper.trade(fiat, 1000, crypto, 10)
    assert tx.from_detail.cost_basis == Decimal(1000)  # 1 EUR == 1 EUR
    assert tx.to_detail.cost_basis == Decimal(100)  # BOUGHT: 1 BTC == 100 EUR

    # Sell 5 BTC for 1000 EUR
    tx = wallet_helper.trade(crypto, 5, fiat, 1000)
    assert tx.from_detail.cost_basis == Decimal(100)  # BOUGHT: 1 BTC == 100 EUR
    assert tx.to_detail.cost_basis == Decimal(200)  # SOLD: 1 BTC == 200 EUR

    # Sell 5 BTC for 2000 EUR
    tx = wallet_helper.trade(crypto, 5, fiat, 2000)
    assert tx.from_detail.cost_basis == Decimal(100)  # BOUGHT: 1 BTC == 100 EUR
    assert tx.to_detail.cost_basis == Decimal(400)  # SOLD: 1 BTC == 400 EUR


@pytest.mark.django_db
def test_cost_basis_fiat_crypto_fiat_trades_fifo():
    """Test calculating cost basis for FIAT -> CRYPTO -> FIAT trades using FIFO"""
    wallet = WalletFactory.create()
    wallet_helper = WalletHelper(wallet)

    fiat = FiatCurrencyFactory.create(symbol="EUR")
    crypto = CryptoCurrencyFactory.create(symbol="BTC")

    # Deposit FIAT to wallet
    wallet_helper.deposit(fiat, 1000)

    # Buy 5 BTC with 400 and 5 BTC with 600 EUR
    tx = wallet_helper.trade(fiat, 400, crypto, 5)
    assert tx.to_detail.cost_basis == Decimal(80)  # 1 BTC == 80 EUR
    tx = wallet_helper.trade(fiat, 600, crypto, 5)
    assert tx.to_detail.cost_basis == Decimal(120)  # 1 BTC == 120 EUR

    # Sell 2 BTC for 200 EUR
    tx = wallet_helper.trade(crypto, 2, fiat, 200)
    assert tx.from_detail.cost_basis == Decimal(80)  # 1 BTC == 100 EUR
    assert tx.to_detail.cost_basis == Decimal(100)  # 1 BTC == 100 EUR

    # Sell 5 BTC for 500 EUR
    tx = wallet_helper.trade(crypto, 5, fiat, 500)
    assert tx.from_detail.cost_basis == Decimal(96)  # 1 BTC == 96 EUR = (3*80 + 2*120) / 5
    assert tx.to_detail.cost_basis == Decimal(100)  # 1 BTC == 100 EUR

    # Sell the remaining 3 BTC for 600 EUR
    tx = wallet_helper.trade(crypto, 3, fiat, 600)
    assert tx.from_detail.cost_basis == Decimal(120)  # 1 BTC == 120 EUR
    assert tx.to_detail.cost_basis == Decimal(200)  # 1 BTC == 400 EUR


@pytest.mark.django_db
def test_cost_basis_fiat_crypto_crypto_fiat_trades_fifo():
    """Test calculating cost basis for FIAT -> CRYPTO -> CRYPTO-> FIAT trades using FIFO"""
    wallet = WalletFactory.create()
    wallet_helper = WalletHelper(wallet)

    fiat = FiatCurrencyFactory.create(symbol="EUR")
    btc = CryptoCurrencyFactory.create(symbol="BTC")
    eth = CryptoCurrencyFactory.create(symbol="ETH")

    # Deposit FIAT to wallet
    wallet_helper.deposit(fiat, 1000)
    wallet_helper.trade(fiat, 600, btc, 6)  # 1 BTC == 100 EUR
    wallet_helper.trade(fiat, 400, btc, 2)  # 1 BTC == 200 EUR

    # Trade 4*100 = 400 EUR BTC to ETH
    tx = wallet_helper.trade(btc, 4, eth, 20)
    assert tx.from_detail.cost_basis == Decimal(100)
    assert tx.to_detail.cost_basis == Decimal(20)  # 1 ETH == 20 EUR

    # Trade 2*100 + 2*200 = 600 EUR to ETH
    tx = wallet_helper.trade(btc, 4, eth, 20)
    assert tx.from_detail.cost_basis == Decimal(150)
    assert tx.to_detail.cost_basis == Decimal(30)  # 1 ETH == 10 EUR

    # Sell all 40 ETH to FIAT
    tx = wallet_helper.trade(eth, 40, fiat, 400)
    assert tx.from_detail.cost_basis == Decimal(25)
    assert tx.to_detail.cost_basis == Decimal(10)  # 1 ETH == 10 EUR
