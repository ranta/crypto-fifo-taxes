import pytest

from crypto_fifo_taxes_tests.factories import (
    CryptoCurrencyFactory,
    CurrencyPriceFactory,
    FiatCurrencyFactory,
    WalletFactory,
)
from crypto_fifo_taxes_tests.utils import WalletHelper


@pytest.mark.django_db()
def test_deposit_and_withdrawal():
    fiat = FiatCurrencyFactory.create(symbol="EUR")
    crypto = CryptoCurrencyFactory.create(symbol="BTC")

    wallet = WalletFactory.create(fiat=fiat)
    wallet_helper = WalletHelper(wallet)

    tx = wallet_helper.deposit(fiat, 1000)
    assert tx.gain == 0

    CurrencyPriceFactory.create(currency=crypto, fiat=fiat, date=wallet_helper.date(), price=1000)
    tx = wallet_helper.deposit(crypto, 1)
    assert tx.to_detail.cost_basis == 1000
    assert tx.gain == 1000

    wallet_helper.tx_time.next_day()
    CurrencyPriceFactory.create(currency=crypto, fiat=fiat, date=wallet_helper.date(), price=5000)
    tx = wallet_helper.withdraw(crypto, 1)
    assert tx.from_detail.cost_basis == 1000
    assert tx.gain == 4000

    tx = wallet_helper.withdraw(fiat, 1000)
    assert tx.gain == 0
