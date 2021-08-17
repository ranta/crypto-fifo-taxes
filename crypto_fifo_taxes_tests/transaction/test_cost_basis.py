from decimal import Decimal

import pytest

from crypto_fifo_taxes_tests.factories import (
    CryptoCurrencyFactory,
    CurrencyPriceFactory,
    FiatCurrencyFactory,
    WalletFactory,
)
from crypto_fifo_taxes_tests.utils import WalletHelper


@pytest.mark.django_db
def test_cost_basis_fiat_crypto_fiat_trades_simple():
    """Test calculating cost basis for FIAT -> CRYPTO -> FIAT trades that don't require using FIFO"""
    fiat = FiatCurrencyFactory.create(symbol="EUR")
    crypto = CryptoCurrencyFactory.create(symbol="BTC")

    wallet = WalletFactory.create(fiat=fiat)
    wallet_helper = WalletHelper(wallet)

    # Deposit FIAT to wallet
    wallet_helper.deposit(fiat, 1000)

    # Buy 10 BTC with 1000 EUR
    tx = wallet_helper.trade(fiat, 1000, crypto, 10)
    assert tx.from_detail.cost_basis == Decimal(1)  # 1 EUR == 1 EUR
    assert tx.to_detail.cost_basis == Decimal(100)  # 1 BTC == 100 EUR

    # Sell 5 BTC for 1000 EUR
    tx = wallet_helper.trade(crypto, 5, fiat, 1000)
    assert tx.from_detail.cost_basis == Decimal(100)  # 1 BTC == 100 EUR
    assert tx.to_detail.cost_basis == Decimal(1)  # 1 EUR == 1 EUR

    # Sell 5 BTC for 2000 EUR
    tx = wallet_helper.trade(crypto, 5, fiat, 2000)
    assert tx.from_detail.cost_basis == Decimal(100)  # 1 BTC == 100 EUR
    assert tx.to_detail.cost_basis == Decimal(1)  # 1 EUR == 1 EUR


@pytest.mark.django_db
def test_cost_basis_fiat_crypto_fiat_trades_fifo():
    """Test calculating cost basis for FIAT -> CRYPTO -> FIAT trades using FIFO"""
    fiat = FiatCurrencyFactory.create(symbol="EUR")
    crypto = CryptoCurrencyFactory.create(symbol="BTC")

    wallet = WalletFactory.create(fiat=fiat)
    wallet_helper = WalletHelper(wallet)

    # Deposit FIAT to wallet
    wallet_helper.deposit(fiat, 1000)

    # Buy 5 BTC with 400 and 5 BTC with 600 EUR
    tx = wallet_helper.trade(fiat, 400, crypto, 5)
    assert tx.to_detail.cost_basis == Decimal(80)  # 1 BTC == 80 EUR
    tx = wallet_helper.trade(fiat, 600, crypto, 5)
    assert tx.to_detail.cost_basis == Decimal(120)  # 1 BTC == 120 EUR

    # Sell 2 BTC for 200 EUR
    tx = wallet_helper.trade(crypto, 2, fiat, 200)
    assert tx.from_detail.cost_basis == Decimal(80)  # 1 BTC == 80 EUR

    # Sell 5 BTC for 500 EUR
    tx = wallet_helper.trade(crypto, 5, fiat, 500)
    assert tx.from_detail.cost_basis == Decimal(96)  # 1 BTC == 96 EUR = (3*80 + 2*120) / 5

    # Sell the remaining 3 BTC for 600 EUR
    tx = wallet_helper.trade(crypto, 3, fiat, 600)
    assert tx.from_detail.cost_basis == Decimal(120)  # 1 BTC == 120 EUR


@pytest.mark.django_db
def test_cost_basis_fiat_crypto_crypto_fiat_trades_fifo():
    """Test calculating cost basis for FIAT -> CRYPTO -> CRYPTO-> FIAT trades using FIFO"""
    fiat = FiatCurrencyFactory.create(symbol="EUR")
    btc = CryptoCurrencyFactory.create(symbol="BTC")
    eth = CryptoCurrencyFactory.create(symbol="ETH")

    wallet = WalletFactory.create(fiat=fiat)
    wallet_helper = WalletHelper(wallet)

    # Deposit FIAT to wallet
    wallet_helper.deposit(fiat, 1000)
    wallet_helper.trade(fiat, 600, btc, 6)  # 1 BTC == 100 EUR
    wallet_helper.trade(fiat, 400, btc, 2)  # 1 BTC == 200 EUR

    # Trade 4*100 = 400 EUR BTC to ETH
    CurrencyPriceFactory.create(currency=btc, fiat=fiat, date=wallet_helper.date(), price=100)
    tx = wallet_helper.trade(btc, 4, eth, 20)
    assert tx.from_detail.cost_basis == Decimal(100)
    assert tx.to_detail.cost_basis == Decimal(20)  # 1 ETH == 20 EUR

    # Trade 2*100 + 2*200 = 600 EUR to ETH
    wallet_helper.tx_time.next_day()
    CurrencyPriceFactory.create(currency=btc, fiat=fiat, date=wallet_helper.date(), price=150)
    tx = wallet_helper.trade(btc, 4, eth, 20)
    assert tx.from_detail.cost_basis == Decimal(150)
    assert tx.to_detail.cost_basis == Decimal(30)  # 1 ETH == 10 EUR

    # Sell all 40 ETH to FIAT
    wallet_helper.tx_time.next_day()
    CurrencyPriceFactory.create(currency=eth, fiat=fiat, date=wallet_helper.date(), price=25)
    tx = wallet_helper.trade(eth, 40, fiat, 400)
    assert tx.from_detail.cost_basis == Decimal(25)


@pytest.mark.django_db
def test_cost_basis_deemed_acquisition_cost():
    """Test that deemed acquisition cost (Hankintameno-olettama) is used whenever applicable"""
    fiat = FiatCurrencyFactory.create(symbol="EUR")
    crypto = CryptoCurrencyFactory.create(symbol="BTC")
    crypto2 = CryptoCurrencyFactory.create(symbol="ETH")

    wallet = WalletFactory.create(fiat=fiat)
    wallet_helper = WalletHelper(wallet)

    # Deposit FIAT to wallet
    wallet_helper.deposit(fiat, 1400)

    # Buy 10 BTC with 1000 EUR
    tx = wallet_helper.trade(fiat, 400, crypto, 4)
    assert tx.to_detail.cost_basis == 100  # 1 BTC == 100 EUR

    tx = wallet_helper.trade(crypto, 1, fiat, 1000)
    # Instead of the original cost basis of 100, it is now 200 because of HMO
    assert tx.from_detail.cost_basis == 200

    tx = wallet_helper.trade(crypto, 1, fiat, 5000)
    assert tx.from_detail.cost_basis == 1000

    CurrencyPriceFactory.create(currency=crypto, fiat=fiat, date=wallet_helper.date(), price=1000)
    CurrencyPriceFactory.create(currency=crypto2, fiat=fiat, date=wallet_helper.date(), price=100)
    tx = wallet_helper.trade(crypto, 1, crypto2, 10, crypto2, 1)
    assert tx.from_detail.cost_basis == 200
    assert tx.gain == 800
    assert tx.fee_amount == 0

    # Buy more BTC at current prices
    wallet_helper.trade(fiat, 1000, crypto, 1)
    # Immediately sell the 2 BTC left in wallet. HMO is used only for the first BTC
    tx = wallet_helper.trade(crypto, 2, fiat, 2000, fiat, 1)
    assert tx.from_detail.cost_basis == 600  # (200 + 1000) / 2
    assert tx.fee_amount == 1  # HMO is not used for every token, so fee is able to be deduced from profits
