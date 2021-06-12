import factory
from factory.django import DjangoModelFactory

from crypto_fifo_taxes.models import Wallet


class WalletFactory(DjangoModelFactory):
    class Meta:
        model = Wallet
        django_get_or_create = (
            "user",
            "name",
        )

    user = factory.SubFactory("crypto_fifo_taxes_tests.factories.UserFactory")
    name = factory.Sequence(lambda n: f"Wallet-{n}: {factory.Faker('word')}")
    icon = None
    fiat = factory.SubFactory("crypto_fifo_taxes_tests.factories.FiatCurrencyFactory")
