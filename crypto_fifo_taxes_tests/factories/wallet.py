import factory
from factory.django import DjangoModelFactory
from faker import Faker

from crypto_fifo_taxes.models import Wallet

fake = Faker()


class WalletFactory(DjangoModelFactory):
    class Meta:
        model = Wallet
        django_get_or_create = (
            "user",
            "name",
        )

    user = factory.SubFactory("crypto_fifo_taxes_tests.factories.UserFactory")
    name = factory.Sequence(lambda n: f"Wallet-{n}: {fake.word()}")
    icon = None
    fiat = factory.SubFactory("crypto_fifo_taxes_tests.factories.FiatCurrencyFactory", symbol="EUR")
