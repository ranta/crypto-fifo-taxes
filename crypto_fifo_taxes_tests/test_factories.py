import pytest

from crypto_fifo_taxes.models import Currency
from crypto_fifo_taxes_tests import factories


@pytest.mark.django_db
def test_user_factory():
    factories.WalletFactory.create()


@pytest.mark.django_db
def test_wallet_factory():
    factories.WalletFactory.create()


@pytest.mark.django_db
def test_fiat_currency_factory():
    factories.FiatCurrencyFactory.create()
    assert Currency.objects.first().is_fiat is True


@pytest.mark.django_db
def test_crypto_currency_factory():
    factories.CryptoCurrencyFactory.create()
    assert Currency.objects.first().is_fiat is False


@pytest.mark.django_db
def test_currency_pair_factory():
    factories.CurrencyPairFactory.create()


@pytest.mark.django_db
def test_currency_price_factory():
    factories.CurrencyPriceFactory.create()


@pytest.mark.django_db
def test_transaction_factory():
    factories.TransactionFactory.create()


@pytest.mark.django_db
def test_transaction_detail_factory():
    factories.TransactionDetailFactory.create()
