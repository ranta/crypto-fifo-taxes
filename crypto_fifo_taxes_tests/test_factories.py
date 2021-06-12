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
def test_wallet_transfer_factory():
    factories.WalletTransferFactory.create()


@pytest.mark.django_db
def test_trade_factory():
    factories.TradeFactory.create()


@pytest.mark.django_db
def test_trade_extra_factory():
    factories.TradeExtraFactory.create()


@pytest.mark.django_db
def test_trade_fee_factory():
    factories.TradeFeeFactory.create()


@pytest.mark.django_db
def test_trade_fee_extra_factory():
    factories.TradeFeeExtraFactory.create()
