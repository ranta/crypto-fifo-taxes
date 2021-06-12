import datetime

import factory.fuzzy
from dateutil.tz import UTC
from factory.django import DjangoModelFactory

from crypto_fifo_taxes.models import WalletTransfer


class WalletTransferFactory(DjangoModelFactory):
    class Meta:
        model = WalletTransfer

    from_wallet = factory.SubFactory("crypto_fifo_taxes_tests.factories.WalletFactory")
    to_wallet = factory.SubFactory("crypto_fifo_taxes_tests.factories.WalletFactory")

    from_currency = factory.SubFactory("crypto_fifo_taxes_tests.factories.CryptoCurrencyFactory")
    to_currency = factory.LazyAttribute(lambda self: self.from_currency)

    from_amount = factory.fuzzy.FuzzyDecimal(1, 1000, precision=8)
    to_amount = factory.LazyAttribute(lambda self: self.from_amount)

    timestamp = factory.fuzzy.FuzzyDateTime(
        datetime.datetime(2010, 1, 1, tzinfo=UTC),
        datetime.datetime(2020, 12, 31, tzinfo=UTC),
    )
