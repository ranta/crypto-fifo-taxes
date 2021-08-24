from decimal import Decimal

import pytest
from django.db.transaction import atomic

from crypto_fifo_taxes.utils.transaction_creator import TransactionCreator
from crypto_fifo_taxes_tests.factories import (
    CryptoCurrencyFactory,
    CurrencyPriceFactory,
    FiatCurrencyFactory,
    WalletFactory,
)
from crypto_fifo_taxes_tests.utils import WalletHelper


@pytest.mark.django_db
def test_fees_paid_with_new_currency():
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
    assert wallet.get_current_balance("BTC") == Decimal("9.99")

    # Trade BTC back to EUR fails, because user has less than 10 BTC due to fees
    with pytest.raises(ValueError):
        with atomic():
            wallet_helper.trade(crypto, 10, fiat, 1000)

    wallet_helper.trade(crypto, Decimal("9.99"), fiat, 999, fiat, 1)
    assert wallet.get_current_balance("BTC") == Decimal(0)
    assert wallet.get_current_balance("EUR") == Decimal(998)


@pytest.mark.django_db
def test_fees_paid_with_original_currency():
    fiat = FiatCurrencyFactory.create(symbol="EUR")
    crypto = CryptoCurrencyFactory.create(symbol="BTC")

    wallet = WalletFactory.create(fiat=fiat)
    wallet_helper = WalletHelper(wallet)

    # Deposit FIAT to wallet
    wallet_helper.deposit(fiat, 1000)

    # Buy 10 BTC with 1000 EUR
    tx = wallet_helper.trade(fiat, 950, crypto, 10, fiat, 50)
    assert tx.to_detail.cost_basis == Decimal(95)  # 1 BTC == 100 EUR
    assert tx.fee_detail.cost_basis == Decimal(1)
    assert tx.fee_detail.quantity == 50
    assert tx.fee_amount == 50
    assert wallet.get_current_balance("BTC") == 10
    assert wallet.get_current_balance("EUR") == 0


@pytest.mark.django_db
def test_fees_with_dedicated_fee_currency():
    fiat = FiatCurrencyFactory.create(symbol="EUR")
    crypto = CryptoCurrencyFactory.create(symbol="BTC")
    fee_currency = CryptoCurrencyFactory.create(symbol="BNB")

    wallet = WalletFactory.create(fiat=fiat)
    wallet_helper = WalletHelper(wallet)

    # Deposit FIAT to wallet
    wallet_helper.deposit(fiat, 520)

    # Buy some BNB to be used as fee currency
    tx = wallet_helper.trade(fiat, 20, fee_currency, 1, fee_currency, Decimal("0.1"))
    assert tx.fee_amount == 20 * Decimal("0.1")  # 2 EUR

    # Buy 5 BTC with 500 EUR
    tx = wallet_helper.trade(fiat, 500, crypto, 5, fee_currency, Decimal("0.1"))
    assert tx.to_detail.cost_basis == Decimal(100)  # 1 BTC == 100 EUR
    assert tx.fee_detail.cost_basis == Decimal(20)  # 1 BNB == 20 EUR
    assert tx.fee_detail.quantity == Decimal("0.1")
    assert tx.fee_amount == 20 * Decimal("0.1")  # 2 EUR

    assert wallet.get_current_balance("BTC") == Decimal(5)
    assert wallet.get_current_balance("BNB") == Decimal("0.8")


@pytest.mark.django_db
def test_fee_withdrawal():
    fiat = FiatCurrencyFactory.create(symbol="EUR")
    crypto = CryptoCurrencyFactory.create(symbol="BTC")

    wallet = WalletFactory.create(fiat=fiat)
    wallet_helper = WalletHelper(wallet)

    # Deposit FIAT to wallet
    CurrencyPriceFactory.create(currency=crypto, fiat=fiat, date=wallet_helper.date(), price=1000)
    wallet_helper.deposit(crypto, 10)
    assert wallet.get_current_balance("BTC") == Decimal(10)

    # Fees should be removed from the `withdrawn amount` instead of from wallet
    tx_creator = TransactionCreator()
    tx_creator.add_fee_detail(wallet=wallet, currency=crypto, quantity=Decimal(1))
    tx_creator.create_withdrawal(
        timestamp=wallet_helper.tx_time.timestamp,
        wallet=wallet,
        currency=crypto,
        quantity=Decimal(10),
    )
    assert wallet.get_current_balance("BTC") == Decimal(0)


@pytest.mark.django_db
def test_fee_transfer():
    fiat = FiatCurrencyFactory.create(symbol="EUR")
    crypto = CryptoCurrencyFactory.create(symbol="BTC")

    wallet_from = WalletFactory.create(fiat=fiat)
    wallet_to = WalletFactory.create(fiat=fiat)
    wallet_helper = WalletHelper(wallet_from)

    wallet_helper.deposit(fiat, 1000)
    wallet_helper.trade(fiat, 1000, crypto, 10)

    # Fees should be removed from the `withdrawn amount` instead of from wallet
    tx_creator = TransactionCreator(timestamp=wallet_helper.tx_time.timestamp)
    tx_creator.add_from_detail(wallet=wallet_from, currency=crypto, quantity=10)
    tx_creator.add_to_detail(wallet=wallet_to, currency=crypto, quantity=10)

    # Fee should be directed to the `TO` wallet when transferring funds.
    tx_creator.add_fee_detail(wallet=wallet_to, currency=crypto, quantity=1)
    tx_creator.create_transfer()
    assert wallet_from.get_current_balance("BTC") == Decimal(0)
    assert wallet_to.get_current_balance("BTC") == Decimal(9)
