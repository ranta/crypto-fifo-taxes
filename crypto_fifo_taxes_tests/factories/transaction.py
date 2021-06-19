import datetime

import factory.fuzzy
from dateutil.tz import UTC
from factory.django import DjangoModelFactory

from crypto_fifo_taxes.enums import TransactionLabel, TransactionType
from crypto_fifo_taxes.models import Transaction, TransactionDetail
from crypto_fifo_taxes_tests.factories.currency import CryptoCurrencyFactory, FiatCurrencyFactory


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
    to_detail = factory.SubFactory("crypto_fifo_taxes_tests.factories.TransactionDetailFactory")
    fee_detail = None
    gain = None
    fee_amount = None


class TransactionDetailFactory(DjangoModelFactory):
    class Meta:
        model = TransactionDetail

    wallet = factory.SubFactory("crypto_fifo_taxes_tests.factories.WalletFactory")
    currency = factory.SubFactory("crypto_fifo_taxes_tests.factories.CryptoCurrencyFactory")
    quantity = factory.fuzzy.FuzzyDecimal(1, 1000, precision=8)
    cost_basis = None

    @staticmethod
    def handle_currency(kwargs):
        """
        Allow passing currency as a string, instead of a Currency object.
        If currency is passed as a string, replace it in kwargs with a `Currency` object
        """
        if isinstance(kwargs.get("currency"), str):
            currency_factory = CryptoCurrencyFactory
            is_fiat = kwargs.pop("is_fiat", False)
            if is_fiat:
                currency_factory = FiatCurrencyFactory
            currency = currency_factory.create(symbol=kwargs.get("currency"))
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
