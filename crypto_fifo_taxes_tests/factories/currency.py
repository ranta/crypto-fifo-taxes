import datetime
import random
import string

import factory.fuzzy
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
    date = factory.fuzzy.FuzzyDate(
        datetime.date(2010, 1, 1),
        datetime.date(2020, 12, 31),
    )
    price = factory.fuzzy.FuzzyDecimal(1, 1000, precision=8)
    market_cap = 0
    volume = 0
