import factory
from factory.django import DjangoModelFactory
from faker import Faker

from crypto_fifo_taxes.models import Wallet

fake = Faker()


class WalletFactory(DjangoModelFactory):
    class Meta:
        model = Wallet
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: f"Wallet-{n}: {fake.word()}")
    icon = None
