import datetime

import pytest
from factory.errors import FactoryError

from crypto_fifo_taxes.models import Currency
from tests import factories


@pytest.mark.django_db()
def test_user_factory():
    factories.UserFactory.create()


@pytest.mark.django_db()
def test_wallet_factory():
    factories.WalletFactory.create()


@pytest.mark.django_db()
def test_crypto_currency_factory():
    factories.CryptoCurrencyFactory.create()
    assert Currency.objects.first().is_fiat is False


@pytest.mark.django_db()
def test_currency_pair_factory():
    factories.CurrencyPairFactory.create()


@pytest.mark.django_db()
def test_currency_price_factory():
    factories.CurrencyPriceFactory.create()


@pytest.mark.django_db()
def test_transaction_factory():
    factories.TransactionFactory.create()


@pytest.mark.django_db()
def test_transaction_detail_factory():
    factories.TransactionDetailFactory.create()


@pytest.mark.django_db()
def test_transaction_detail_factory_currency_as_string():
    currency = factories.CryptoCurrencyFactory.create(symbol="BTC")
    factories.TransactionDetailFactory.create(currency=currency)
    factories.TransactionDetailFactory.create(currency="BTC")

    # Currency should still be saved, even if detail is not saved
    factories.TransactionDetailFactory.build(currency="ETH")
    assert Currency.objects.get(symbol="ETH")


@pytest.mark.django_db()
def test_snapshot_factory():
    with pytest.raises(FactoryError):
        # Date not defined
        factories.SnapshotFactory.create()

    factories.SnapshotFactory.create(date=datetime.date(2020, 1, 1))


@pytest.mark.django_db()
def test_snapshot_balance_factory():
    with pytest.raises(FactoryError):
        # Snapshot not defined
        factories.SnapshotBalanceFactory.create()

    factories.SnapshotBalanceFactory.create(snapshot__date=datetime.date(2020, 1, 1))
