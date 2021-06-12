import datetime

import factory.fuzzy
from dateutil.tz import UTC
from factory.django import DjangoModelFactory

from crypto_fifo_taxes.enums import TradeType
from crypto_fifo_taxes.models import Trade, TradeExtra, TradeFee
from crypto_fifo_taxes.models.trade import TradeFeeExtra


class TradeFactory(DjangoModelFactory):
    class Meta:
        model = Trade

    wallet = factory.SubFactory("crypto_fifo_taxes_tests.factories.WalletFactory")
    pair = factory.SubFactory("crypto_fifo_taxes_tests.factories.CurrencyPairFactory")

    price = factory.fuzzy.FuzzyDecimal(1, 1000, precision=8)
    quantity = factory.fuzzy.FuzzyDecimal(1, 1000, precision=8)
    total_price = factory.LazyAttribute(lambda self: self.price * self.quantity)
    trade_type = TradeType.BUY
    timestamp = factory.fuzzy.FuzzyDateTime(
        datetime.datetime(2010, 1, 1, tzinfo=UTC),
        datetime.datetime(2020, 12, 31, tzinfo=UTC),
    )


class TradeExtraFactory(DjangoModelFactory):
    class Meta:
        model = TradeExtra

    trade = factory.SubFactory("crypto_fifo_taxes_tests.factories.TradeFactory")
    from_cost_basis = factory.fuzzy.FuzzyDecimal(1, 1000, precision=8)
    to_cost_basis = factory.fuzzy.FuzzyDecimal(1, 1000, precision=8)


class TradeFeeFactory(DjangoModelFactory):
    class Meta:
        model = TradeFee

    trade = factory.SubFactory("crypto_fifo_taxes_tests.factories.TradeFactory")
    quantity = factory.fuzzy.FuzzyDecimal(0.0001, 1, precision=8)
    currency = factory.SubFactory("crypto_fifo_taxes_tests.factories.CryptoCurrencyFactory")


class TradeFeeExtraFactory(DjangoModelFactory):
    class Meta:
        model = TradeFeeExtra

    fee = factory.SubFactory("crypto_fifo_taxes_tests.factories.TradeFeeFactory")
    from_cost_basis = factory.fuzzy.FuzzyDecimal(1, 1000, precision=8)
    to_cost_basis = factory.fuzzy.FuzzyDecimal(1, 1000, precision=8)
