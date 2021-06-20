from datetime import datetime, timedelta
from decimal import Decimal

import pytest
import pytz

from crypto_fifo_taxes_tests.factories import CryptoCurrencyFactory, FiatCurrencyFactory, WalletFactory
from crypto_fifo_taxes_tests.factories.utils import WalletHelper


@pytest.mark.django_db
def test_calc_simple_fiat_trades_cost_basis():
    wallet = WalletFactory.create()
    wallet_helper = WalletHelper(wallet)

    crypto = CryptoCurrencyFactory.create(symbol="BTC")
    fiat = FiatCurrencyFactory.create(symbol="EUR")

    # Deposit FIAT to wallet
    tx_time = datetime(2010, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)  # 12:00 on day 0
    wallet_helper.deposit(fiat, 1000, timestamp=tx_time)

    # Buy 10 BTC with 1000 EUR
    tx = wallet_helper.buy_crypto(crypto, 10, fiat, 1000, tx_time + timedelta(hours=1))
    assert tx.to_detail.cost_basis == Decimal(100)  # 1 BTC == 100 EUR

    # Sell 5 BTC for 1000 EUR
    tx = wallet_helper.sell_crypto(crypto, 5, fiat, 1000, tx_time + timedelta(days=2))
    assert tx.to_detail.cost_basis == Decimal(200)  # 1 BTC == 200 EUR

    # Sell 5 BTC for 2000 EUR
    tx = wallet_helper.sell_crypto(crypto, 5, fiat, 2000, tx_time + timedelta(days=3))
    assert tx.to_detail.cost_basis == Decimal(400)  # 1 BTC == 400 EUR


