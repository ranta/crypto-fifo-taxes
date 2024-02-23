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

    transaction_type = TransactionType.DEPOSIT
    transaction_label = TransactionLabel.UNKNOWN
    from_detail = None
    to_detail = factory.SubFactory("tests.factories.TransactionDetailFactory")
    fee_detail = None
    gain = None
    fee_amount = None
    tx_id = ""


class TransactionDetailFactory(DjangoModelFactory):
    class Meta:
        model = TransactionDetail

    wallet = factory.SubFactory("tests.factories.WalletFactory")
    currency = factory.SubFactory("tests.factories.CryptoCurrencyFactory")
    quantity = factory.fuzzy.FuzzyDecimal(1, 1000, precision=8)
    cost_basis = None

    @staticmethod
    def handle_currency(kwargs):
        """
        Allow passing currency as a string, instead of a Currency object.
        If currency is passed as a string, replace it in kwargs with a `Currency` object
        """
        from tests.utils import get_test_currency

        currency = get_test_currency(kwargs.get("currency"), kwargs.pop("is_fiat", False))
        kwargs.update({"currency": currency})

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        manager = cls._get_manager(model_class)
        cls.handle_currency(kwargs)
        return manager.create(*args, **kwargs)

    @classmethod
    def _build(cls, model_class, *args, **kwargs):
        cls.handle_currency(kwargs)  # Currency will be created, even if this object is only built
        return model_class(**kwargs)
