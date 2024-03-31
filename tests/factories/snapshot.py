from factory import SubFactory
from factory.django import DjangoModelFactory
from faker import Faker

from crypto_fifo_taxes.models import Snapshot, SnapshotBalance

fake = Faker()


class SnapshotFactory(DjangoModelFactory):
    class Meta:
        model = Snapshot
        django_get_or_create = ["date"]

    worth = None
    cost_basis = None
    deposits = None


class SnapshotBalanceFactory(DjangoModelFactory):
    class Meta:
        model = SnapshotBalance
        django_get_or_create = ["snapshot", "currency"]

    snapshot = SubFactory("tests.factories.SnapshotFactory")
    currency = SubFactory("tests.factories.CryptoCurrencyFactory")
    quantity = None
    cost_basis = None
