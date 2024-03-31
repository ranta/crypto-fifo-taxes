import pytest

from crypto_fifo_taxes.utils.currency import get_fiat_currency
from tests.factories import (
    CryptoCurrencyFactory,
    CurrencyPriceFactory,
    WalletFactory,
)
from tests.utils import WalletHelper


@pytest.mark.django_db()
def test_deposit_and_withdrawal():
    fiat = get_fiat_currency()
    crypto = CryptoCurrencyFactory.create(symbol="BTC")

    wallet = WalletFactory.create()
    wallet_helper = WalletHelper(wallet)

    tx = wallet_helper.deposit(fiat, 1000)
    assert tx.gain == 0

    CurrencyPriceFactory.create(currency=crypto, date=wallet_helper.date, price=1000)
    tx = wallet_helper.deposit(crypto, 1)
    assert tx.to_detail.cost_basis == 1000
    assert tx.gain == 1000

    wallet_helper.tx_time.next_day()
    CurrencyPriceFactory.create(currency=crypto, date=wallet_helper.date, price=5000)
    tx = wallet_helper.withdraw(crypto, 1)
    assert tx.from_detail.cost_basis == 1000
    assert tx.gain == 4000

    tx = wallet_helper.withdraw(fiat, 1000)
    assert tx.gain == 0
