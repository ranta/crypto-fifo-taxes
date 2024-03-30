import random
import string
from datetime import date, timedelta
from decimal import Decimal

import factory.fuzzy
from enumfields import Enum
from factory.django import DjangoModelFactory

from crypto_fifo_taxes.models import Currency, CurrencyPair, CurrencyPrice

# Commonly used Coingecko currency ids, to reduce the need for API calls
CG_IDS = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "doge": "dogecoin",
    "bnb": "binancecoin",
    "usdt": "tether",
}


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

    name = factory.LazyAttribute(lambda self: f"CRYPTO-{self.symbol}")
    cg_id = factory.LazyAttribute(lambda self: CG_IDS.get(self.symbol.lower(), f"CG-ID-{self.symbol}"))
    icon = None
    is_fiat = False


class FiatCurrencyFactory(CryptoCurrencyFactory):
    name = factory.LazyAttribute(lambda self: f"FIAT-{self.symbol}")
    cg_id = factory.LazyAttribute(lambda self: self.symbol.lower())
    is_fiat = True


class CurrencyPairFactory(DjangoModelFactory):
    class Meta:
        model = CurrencyPair
        django_get_or_create = ("buy", "sell")

    buy = factory.SubFactory("tests.factories.CryptoCurrencyFactory")
    sell = factory.SubFactory("tests.factories.CryptoCurrencyFactory")
    symbol = factory.LazyAttribute(lambda self: f"{self.buy.symbol}{self.sell.symbol}")


class CurrencyPriceFactory(DjangoModelFactory):
    class Meta:
        model = CurrencyPrice
        django_get_or_create = ("currency", "date")

    currency = factory.SubFactory("tests.factories.CryptoCurrencyFactory")
    date = factory.fuzzy.FuzzyDate(date(2010, 1, 1), date(2020, 12, 31))
    price = factory.fuzzy.FuzzyDecimal(1, 1000, precision=8)
    market_cap = 0
    volume = 0

    @staticmethod
    def handle_currency(kwargs):
        """Allow passing currency as a string, instead of a Currency object."""
        from tests.utils import get_test_currency

        kwargs.update(
            {
                "currency": get_test_currency(kwargs.get("currency"), False),
            }
        )

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        manager = cls._get_manager(model_class)
        cls.handle_currency(kwargs)
        return manager.create(*args, **kwargs)

    @classmethod
    def _build(cls, model_class, *args, **kwargs):
        cls.handle_currency(kwargs)  # Currency will be created, even if this object is only built and saved to db
        return model_class(**kwargs)


class PriceTrend(Enum):
    BEAR_FAST = -3
    BEAR_MEDIUM = -2
    BEAR_SLOW = -1
    FLAT = 0
    BULL_SLOW = 1
    BULL_MEDIUM = 2
    BULL_FAST = 3


def create_currency_price_history(
    currency: Currency | str,
    start_price: Decimal | int = Decimal(1000),
    trend: PriceTrend = PriceTrend.BULL_SLOW,
    start_date: date | None = None,
    days: int = 31,
):
    """Create linearly changing price history for a currency."""
    from tests.utils import get_test_currency

    currency = get_test_currency(currency, is_fiat=False)
    if start_date is None:
        start_date = date(2010, 1, 1)
    assert days > 0

    for day in range(days):
        CurrencyPriceFactory.create(
            currency=currency,
            date=start_date + timedelta(days=day),
            # Price changes by X% of the start_price each day
            price=start_price + (start_price * trend.value * day / 100),
        )
