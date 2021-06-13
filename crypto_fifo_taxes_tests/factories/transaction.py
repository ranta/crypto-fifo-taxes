import datetime

import factory.fuzzy
from dateutil.tz import UTC
from factory.django import DjangoModelFactory

from crypto_fifo_taxes.enums import TransactionLabel, TransactionType
from crypto_fifo_taxes.models import Transaction, TransactionDetail


class TransactionFactory(DjangoModelFactory):
    class Meta:
        model = Transaction

    timestamp = factory.fuzzy.FuzzyDateTime(
        datetime.datetime(2010, 1, 1, tzinfo=UTC),
        datetime.datetime(2020, 12, 31, tzinfo=UTC),
    )

    transaction_type = TransactionType.TRADE
    transaction_label = TransactionLabel.UNKNOWN
    tx_from = None
    tx_to = factory.SubFactory("crypto_fifo_taxes_tests.factories.TransactionDetailFactory")
    tx_fee = None
    gain = None
    fee_amount = None


class TransactionDetailFactory(DjangoModelFactory):
    class Meta:
        model = TransactionDetail

    wallet = factory.SubFactory("crypto_fifo_taxes_tests.factories.WalletFactory")
    currency = factory.SubFactory("crypto_fifo_taxes_tests.factories.CryptoCurrencyFactory")
    quantity = factory.fuzzy.FuzzyDecimal(1, 1000, precision=8)
    cost_basis = None
