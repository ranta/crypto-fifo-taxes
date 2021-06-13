import pytest

from crypto_fifo_taxes.models import Currency
from crypto_fifo_taxes_tests import factories


@pytest.mark.django_db
def test_wallet_get_currencies():
    wallet = factories.WalletFactory.create()

    # Create a deposit
    for i in range(0, 10):
        factories.TransactionFactory.create(to_detail=factories.TransactionDetailFactory.create(wallet=wallet))

    currencies = wallet.get_currencies()
    assert len(currencies) == 10
    assert Currency.objects.last().pk in currencies
