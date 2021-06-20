from datetime import date, datetime
from decimal import Decimal

import pytest
import pytz

from crypto_fifo_taxes.models import CurrencyPrice
from crypto_fifo_taxes_tests.factories import CryptoCurrencyFactory, FiatCurrencyFactory, WalletFactory
from crypto_fifo_taxes_tests.factories.currency import create_currency_price_history
from crypto_fifo_taxes_tests.factories.utils import WalletHelper


@pytest.mark.django_db
def test_calc_cost_basis():
    wallet = WalletFactory.create()
    wallet_helper = WalletHelper(wallet)

    crypto = CryptoCurrencyFactory.create(symbol="BTC")
    fiat = FiatCurrencyFactory.create(symbol="EUR")

    create_currency_price_history(crypto, fiat, start_date=date(2010, 1, 1))
    # Price on day 0
    assert CurrencyPrice.objects.get(currency=crypto, fiat=fiat, date=date(2010, 1, 1)).price == Decimal(1000)
    # Price on last day, after 30 days of increase
    assert CurrencyPrice.objects.get(currency=crypto, fiat=fiat, date=date(2010, 1, 31)).price == Decimal(1300)
