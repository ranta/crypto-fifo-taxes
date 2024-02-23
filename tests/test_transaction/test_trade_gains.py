from decimal import Decimal

import pytest

from tests.factories import (
    CryptoCurrencyFactory,
    CurrencyPriceFactory,
    FiatCurrencyFactory,
    WalletFactory,
)
from tests.utils import WalletHelper


@pytest.mark.django_db()
def test_gain_fiat_crypto_crypto_fiat_trades():
    """Test calculating profit for FIAT -> CRYPTO -> CRYPTO -> FIAT trades"""
    fiat = FiatCurrencyFactory.create(symbol="EUR")
    btc = CryptoCurrencyFactory.create(symbol="BTC")
    eth = CryptoCurrencyFactory.create(symbol="ETH")

    wallet = WalletFactory.create(fiat=fiat)
    wallet_helper = WalletHelper(wallet)

    # Deposit FIAT to wallet
    wallet_helper.deposit(fiat, 2000)

    # Buy 4 BTC at different prices
    wallet_helper.trade(fiat, 1200, btc, 2)  # 1 BTC == 600 EUR
    wallet_helper.trade(fiat, 800, btc, 2)  # 1 BTC == 400 EUR

    wallet_helper.tx_time.next_day()
    CurrencyPriceFactory.create(currency=btc, fiat=fiat, date=wallet_helper.date(), price=900)
    CurrencyPriceFactory.create(currency=eth, fiat=fiat, date=wallet_helper.date(), price=90)

    # Trade 1 BTC to 10 ETH
    tx = wallet_helper.trade(btc, 1, eth, 10)
    assert tx.from_detail.cost_basis == Decimal(600)  # 1 BTC == 600 EUR
    assert tx.to_detail.cost_basis == Decimal(90)  # 1 ETH == 90 EUR
    assert tx.gain == Decimal(300)  # 900 - 600 = 300 EUR in realized profit

    wallet_helper.tx_time.next_day()
    CurrencyPriceFactory.create(currency=btc, fiat=fiat, date=wallet_helper.date(), price=1200)
    CurrencyPriceFactory.create(currency=eth, fiat=fiat, date=wallet_helper.date(), price=120)

    # Trade 2 BTC to 20 ETH
    tx = wallet_helper.trade(btc, 2, eth, 20)
    assert tx.from_detail.cost_basis == Decimal(500)  # == (600 + 400) / 2 (BTC came from two different cost basis)
    assert tx.to_detail.cost_basis == Decimal(120)
    assert tx.gain == Decimal(1400)  # 1200 * 2 - (600 + 400)

    wallet_helper.tx_time.next_day()
    CurrencyPriceFactory.create(currency=btc, fiat=fiat, date=wallet_helper.date(), price=1000)
    CurrencyPriceFactory.create(currency=eth, fiat=fiat, date=wallet_helper.date(), price=120)

    # Sell remaining 1 BTC to FIAT
    tx = wallet_helper.trade(btc, 1, fiat, 500)
    assert tx.from_detail.cost_basis == Decimal(400)
    assert tx.to_detail.cost_basis == 1
    assert tx.gain == Decimal(100)

    # Sell 15 (half) of ETH to FIAT
    tx = wallet_helper.trade(eth, 15, fiat, 1800)  # 1 ETH == 120 EUR
    assert tx.from_detail.cost_basis == Decimal(100)  # (10*90 + 5*120) / 15
    assert tx.to_detail.cost_basis == 1
    assert tx.gain == Decimal(300)  # (120 - 100) * 15

    wallet_helper.tx_time.next_day()
    CurrencyPriceFactory.create(currency=eth, fiat=fiat, date=wallet_helper.date(), price=100)

    # Sell all 15 ETH to FIAT
    tx = wallet_helper.trade(eth, 15, fiat, 1500)  # 1 ETH == 100 EUR
    assert tx.from_detail.cost_basis == Decimal(120)
    assert tx.gain == Decimal(-300)  # (100 - 120) * 15

    # 2000 + 300 + 1400 + 100 + 300 - 300
    assert wallet.get_current_balance("EUR") == Decimal(3800)
