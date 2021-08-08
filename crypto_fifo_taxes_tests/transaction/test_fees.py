from decimal import Decimal

import pytest
from django.db.transaction import atomic

from crypto_fifo_taxes_tests.factories import CryptoCurrencyFactory, FiatCurrencyFactory, WalletFactory
from crypto_fifo_taxes_tests.utils import WalletHelper


@pytest.mark.django_db
def test_fees_simple():
    fiat = FiatCurrencyFactory.create(symbol="EUR")
    crypto = CryptoCurrencyFactory.create(symbol="BTC")

    wallet = WalletFactory.create(fiat=fiat)
    wallet_helper = WalletHelper(wallet)

    # Deposit FIAT to wallet
    wallet_helper.deposit(fiat, 1000)

    # Buy 10 BTC with 1000 EUR
    tx = wallet_helper.trade(fiat, 1000, crypto, 10, crypto, Decimal("0.01"))
    assert tx.to_detail.cost_basis == Decimal(100)  # 1 BTC == 100 EUR
    assert tx.fee_detail.cost_basis == Decimal(100)  # 1 BTC == 100 EUR
    assert tx.fee_detail.quantity == Decimal("0.01")
    assert tx.fee_amount == 1  # == 100 * 0.01

    # Trade BTC back to EUR fails, because user has less than 10 BTC due to fees
    with pytest.raises(ValueError):
        with atomic():
            wallet_helper.trade(crypto, 10, fiat, 1000)

    wallet_helper.trade(crypto, Decimal("9.99"), fiat, 998, fiat, 1)
    assert wallet.get_current_balance("BTC") == Decimal(0)
