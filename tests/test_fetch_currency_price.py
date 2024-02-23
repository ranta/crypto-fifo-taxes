import datetime
from decimal import Decimal

import pytest

from crypto_fifo_taxes.models import Currency
from crypto_fifo_taxes.utils.coingecko import coingecko_request_price_history, fetch_currency_price
from tests.factories import CryptoCurrencyFactory, FiatCurrencyFactory


@pytest.mark.django_db()
def test_gc_request_history():
    crypto = CryptoCurrencyFactory.create(name="Bitcoin", symbol="BTC")
    response_json = coingecko_request_price_history(currency=crypto, date=datetime.date(2020, 1, 1))

    assert response_json is not None, "Error connecting to Coingecko API"

    assert response_json["symbol"] == "btc"
    assert response_json["market_data"]["current_price"]["eur"] == 6412.84639784161  # Read directly form json
    assert "image" in response_json


@pytest.mark.django_db()
def test_fetch_currency_price():
    FiatCurrencyFactory.create(name="Euro", symbol="EUR")
    FiatCurrencyFactory.create(name="US Dollar", symbol="USD")
    crypto = CryptoCurrencyFactory.create(name="Bitcoin", symbol="BTC")

    fetch_currency_price(currency=crypto, date=datetime.date(2020, 1, 1))

    crypto = Currency.objects.get(symbol="BTC")
    assert crypto.icon is not None
    assert crypto.prices.get(fiat__symbol="EUR").price == Decimal("6412.84639784161")
    assert crypto.prices.get(fiat__symbol="USD").price == Decimal("7195.153895430029")
