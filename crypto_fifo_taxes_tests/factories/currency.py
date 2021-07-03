import random
import string
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, Union

import factory.fuzzy
from enumfields import Enum
from factory.django import DjangoModelFactory

from crypto_fifo_taxes.models import Currency, CurrencyPair, CurrencyPrice


class CryptoCurrencyFactory(DjangoModelFactory):
    class Meta:
        model = Currency
        django_get_or_create = ("symbol",)

    @factory.sequence
    def symbol(n):
        """
        Always generate a unique symbol for new currencies.

        This prevents returning an existing currency with the wrong `is_fiat` value
        if a currency with the same symbol has already been created.
        """
        return "".join(random.choices(string.ascii_uppercase, k=3)) + f".{n}"

    name = factory.LazyAttribute(lambda self: f"Fiat Currency: {self.symbol}")
    icon = None
    is_fiat = False


class FiatCurrencyFactory(CryptoCurrencyFactory):
    is_fiat = True


class CurrencyPairFactory(DjangoModelFactory):
    class Meta:
        model = CurrencyPair
        django_get_or_create = ("buy", "sell")

    buy = factory.SubFactory("crypto_fifo_taxes_tests.factories.CryptoCurrencyFactory")
    sell = factory.SubFactory("crypto_fifo_taxes_tests.factories.CryptoCurrencyFactory")
    symbol = factory.LazyAttribute(lambda self: f"{self.buy.symbol}{self.sell.symbol}")


class CurrencyPriceFactory(DjangoModelFactory):
    class Meta:
        model = CurrencyPrice
        django_get_or_create = ("currency", "date", "fiat")

    currency = factory.SubFactory("crypto_fifo_taxes_tests.factories.CryptoCurrencyFactory")
    fiat = factory.SubFactory("crypto_fifo_taxes_tests.factories.FiatCurrencyFactory")
    date = factory.fuzzy.FuzzyDate(date(2010, 1, 1), date(2020, 12, 31))
    price = factory.fuzzy.FuzzyDecimal(1, 1000, precision=8)
    market_cap = 0
    volume = 0


class PriceTrend(Enum):
    BEAR_FAST = -3
    BEAR_MEDIUM = -2
    BEAR_SLOW = -1
    FLAT = 0
    BULL_SLOW = 1
    BULL_MEDIUM = 2
    BULL_FAST = 3


def create_currency_price_history(
    currency: Union[Currency, str],
    fiat: Union[Currency, str],
    start_price: Union[Decimal, int] = Decimal(1000),
    trend: PriceTrend = PriceTrend.BULL_SLOW,
    start_date: Optional[date] = None,
    days: int = 31,
):
    """Create linearly changing price history for a currency."""
    from crypto_fifo_taxes_tests.utils import get_currency

    currency = get_currency(currency, is_fiat=False)
    fiat = get_currency(fiat, is_fiat=True)
    if start_date is None:
        start_date = date(2010, 1, 1)
    assert days > 0

    for day in range(0, days):
        CurrencyPriceFactory.create(
            currency=currency,
            fiat=fiat,
            date=start_date + timedelta(days=day),
            # Price changes by X% of the start_price each day
            price=start_price + (start_price * trend.value * day / 100),
        )
