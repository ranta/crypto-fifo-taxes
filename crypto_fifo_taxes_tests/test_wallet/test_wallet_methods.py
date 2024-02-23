from decimal import Decimal

import pytest
from django.db.transaction import atomic

from crypto_fifo_taxes.models import Currency
from crypto_fifo_taxes_tests.factories import (
    CryptoCurrencyFactory,
    CurrencyPriceFactory,
    TransactionDetailFactory,
    TransactionFactory,
    WalletFactory,
)
from crypto_fifo_taxes_tests.utils import WalletHelper


@pytest.mark.django_db()
def test_wallet_get_used_currency_ids():
    wallet = WalletFactory.create()

    # Create deposits
    TransactionFactory.create(to_detail=TransactionDetailFactory.create(wallet=wallet, currency="BTC"))
    for i in range(0, 9):
        TransactionFactory.create(to_detail=TransactionDetailFactory.create(wallet=wallet))

    currencies = wallet.get_used_currency_ids()
    assert len(currencies) == 10
    assert Currency.objects.last().pk in currencies
    assert Currency.objects.get(symbol="BTC").pk in currencies


@pytest.mark.django_db()
def test_wallet_get_current_balance_deposit_and_withdrawal_single_currency():
    wallet = WalletFactory.create()
    wallet_helper = WalletHelper(wallet)
    CurrencyPriceFactory.create(currency="BTC", fiat="EUR", date=wallet_helper.date(), price=1000)

    wallet_helper.deposit(currency="BTC", quantity=5)
    wallet_helper.deposit(currency="BTC", quantity=10)
    wallet_helper.withdraw(currency="BTC", quantity=Decimal("2.5"))

    assert len(wallet.get_current_balance()) == 1
    assert wallet.get_current_balance("BTC") == Decimal("12.5")


@pytest.mark.django_db()
def test_wallet_get_current_balance_deposit_and_withdrawal_multiple_currencies():
    wallet = WalletFactory.create()
    wallet_helper = WalletHelper(wallet)
    CurrencyPriceFactory.create(currency="BTC", fiat="EUR", date=wallet_helper.date())
    CurrencyPriceFactory.create(currency="ETH", fiat="EUR", date=wallet_helper.date())
    CurrencyPriceFactory.create(currency="NANO", fiat="EUR", date=wallet_helper.date())
    CurrencyPriceFactory.create(currency="DOGE", fiat="EUR", date=wallet_helper.date())

    # Simple deposit + withdrawal
    wallet_helper.deposit(currency="BTC", quantity=8)
    wallet_helper.withdraw(currency="BTC", quantity=5)

    # Deposit and withdraw everything
    wallet_helper.deposit(currency="ETH", quantity=5)
    wallet_helper.withdraw(currency="ETH", quantity=5)

    # Just deposit
    wallet_helper.deposit(currency="NANO", quantity=1000)

    # Withdraw more than wallet has balance
    with pytest.raises(ValueError):
        with atomic():
            wallet_helper.withdraw(currency="DOGE", quantity=Decimal("42069.1337"))

    balances = wallet.get_current_balance(exclude_zero_balances=False)
    assert len(balances) == 3

    assert balances["BTC"] == 3
    assert balances["ETH"] == 0
    assert balances["NANO"] == 1000
    assert "DOGE" not in balances


@pytest.mark.django_db()
def test_get_consumable_currency_balances():
    wallet = WalletFactory.create()
    wallet_helper = WalletHelper(wallet)

    CurrencyPriceFactory.create(currency="BTC", fiat="ADA", date=wallet_helper.date())
    crypto = CryptoCurrencyFactory.create(symbol="ADA")

    # No deposits, nothing should be returned
    assert len(wallet.get_consumable_currency_balances(crypto)) == 0

    # Deposit some cryptocurrency to wallet in two separate events
    wallet_helper.deposit(crypto, quantity=100)
    wallet_helper.deposit(crypto, quantity=50)
    currencies = wallet.get_consumable_currency_balances(crypto)
    assert len(currencies) == 2
    assert currencies[0].quantity_left == 100
    assert currencies[1].quantity_left == 150
    # Test the method with quantity kwarg
    assert len(wallet.get_consumable_currency_balances(crypto, quantity=99)) == 1
    assert len(wallet.get_consumable_currency_balances(crypto, quantity=101)) == 2
    assert len(wallet.get_consumable_currency_balances(crypto, quantity=1000)) == 2

    # Withdraw a part of the funds
    wallet_helper.withdraw(crypto, quantity=20)
    currencies = wallet.get_consumable_currency_balances(crypto)
    assert len(currencies) == 2
    assert currencies[0].quantity_left == 80
    assert currencies[1].quantity_left == 130

    # Withdraw enough to consume the first deposit and part of the second
    wallet_helper.withdraw(crypto, quantity=100)
    currencies = wallet.get_consumable_currency_balances(crypto)
    assert len(currencies) == 1
    assert currencies[0].quantity_left == 30

    # Everything is withdrawn, nothing should be returned anymore
    wallet_helper.withdraw(crypto, quantity=30)
    assert len(wallet.get_consumable_currency_balances(crypto)) == 0
