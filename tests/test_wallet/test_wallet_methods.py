import datetime
from decimal import Decimal

import pytest
from django.db.transaction import atomic

from crypto_fifo_taxes.exceptions import InsufficientFundsError
from crypto_fifo_taxes.models import Currency
from tests.factories import (
    CryptoCurrencyFactory,
    CurrencyPriceFactory,
    FiatCurrencyFactory,
    TransactionDetailFactory,
    TransactionFactory,
    WalletFactory,
)
from tests.utils import WalletHelper


@pytest.mark.django_db()
def test_wallet_get_used_currency_ids():
    wallet = WalletFactory.create()

    # Create deposits
    TransactionFactory.create(to_detail=TransactionDetailFactory.create(wallet=wallet, currency="BTC"))
    for _i in range(9):
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
    with pytest.raises(InsufficientFundsError), atomic():
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

    CurrencyPriceFactory.create(currency="BTC", fiat="EUR", date=wallet_helper.date())
    crypto = CryptoCurrencyFactory.create(symbol="BTC")

    # No deposits, nothing should be returned
    assert len(wallet.get_consumable_currency_balances(crypto)) == 0

    # Deposit some cryptocurrency to wallet in two separate events
    wallet_helper.deposit(crypto, quantity=100)
    wallet_helper.deposit(crypto, quantity=50)

    # Current balance = 150
    currencies = wallet.get_consumable_currency_balances(crypto)
    assert len(currencies) == 2
    assert currencies[0].quantity_left == 100
    assert currencies[1].quantity_left == 150

    # Test the method with quantity kwarg
    currencies = wallet.get_consumable_currency_balances(crypto, quantity=99)
    assert len(currencies) == 1
    assert currencies[0].quantity_left == 100

    currencies = wallet.get_consumable_currency_balances(crypto, quantity=101)
    assert len(currencies) == 2
    assert currencies[0].quantity_left == 100
    assert currencies[1].quantity_left == 150

    currencies = wallet.get_consumable_currency_balances(crypto, quantity=1000)
    assert len(currencies) == 2
    assert currencies[0].quantity_left == 100
    assert currencies[1].quantity_left == 150

    # Withdraw a part of the funds
    wallet_helper.withdraw(crypto, quantity=20)
    # Current balance = 130
    currencies = wallet.get_consumable_currency_balances(crypto)
    assert len(currencies) == 2
    assert currencies[0].quantity_left == 80
    assert currencies[1].quantity_left == 130

    # Withdraw enough to consume the first deposit and part of the second
    # Current balance = 30
    wallet_helper.withdraw(crypto, quantity=100)
    currencies = wallet.get_consumable_currency_balances(crypto)
    assert len(currencies) == 1
    assert currencies[0].quantity_left == 30

    # Everything is withdrawn, nothing should be returned anymore
    # Current balance = 0
    wallet_helper.withdraw(crypto, quantity=30)
    assert len(wallet.get_consumable_currency_balances(crypto)) == 0


@pytest.mark.django_db()
def test_get_consumable_currency_balances__insufficient_funds():
    wallet = WalletFactory.create()
    wallet_helper = WalletHelper(wallet)

    CurrencyPriceFactory.create(currency="BTC", fiat="EUR", date=wallet_helper.date())
    crypto = CryptoCurrencyFactory.create(symbol="BTC")

    # Deposit some cryptocurrency to wallet in two separate events
    wallet_helper.deposit(crypto, quantity=100)
    wallet_helper.deposit(crypto, quantity=250)

    # Current balance = 350
    currencies = wallet.get_consumable_currency_balances(crypto)
    assert len(currencies) == 2
    assert currencies[0].quantity_left == 100
    assert currencies[1].quantity_left == 350

    # Withdraw more than should be allowed
    with pytest.raises(InsufficientFundsError):
        wallet_helper.withdraw(crypto, quantity=400)


@pytest.mark.django_db()
def test_get_consumable_currency_balances__get_last_consumable_balance():
    wallet = WalletFactory.create()
    wallet_helper = WalletHelper(wallet)

    CurrencyPriceFactory.create(currency="BTC", fiat="EUR", date=wallet_helper.date())
    crypto = CryptoCurrencyFactory.create(symbol="BTC")

    tx_1 = wallet_helper.deposit(crypto, quantity=100)
    tx_2 = wallet_helper.deposit(crypto, quantity=200)
    tx_3 = wallet_helper.withdraw(crypto, quantity=150)
    tx_4 = wallet_helper.deposit(crypto, quantity=100)

    # Current balance = 250
    currencies = wallet.get_consumable_currency_balances(crypto)
    assert len(currencies) == 2
    assert currencies[0].quantity_left == 150
    assert currencies[1].quantity_left == 250

    assert tx_1.to_detail.get_last_consumable_balance().quantity_left == 100
    assert tx_2.to_detail.get_last_consumable_balance().quantity_left == 300
    assert tx_3.from_detail.get_last_consumable_balance().quantity_left == 150
    assert tx_4.to_detail.get_last_consumable_balance().quantity_left == 250


@pytest.mark.django_db()
def test_get_consumable_currency_balances__same_timestamp():
    wallet = WalletFactory.create()
    wallet_helper = WalletHelper(wallet)

    crypto = CryptoCurrencyFactory.create(symbol="BTC")
    CurrencyPriceFactory.create(currency=crypto, fiat=wallet.fiat, date=wallet_helper.date())

    # Deposit some cryptocurrency to wallet in two separate events
    timestamp = datetime.datetime.combine(wallet_helper.date(), datetime.time(12))
    tx_1 = wallet_helper.deposit(crypto, quantity=100, timestamp=timestamp)
    tx_2 = wallet_helper.deposit(crypto, quantity=200, timestamp=timestamp)

    assert tx_1.timestamp == tx_2.timestamp - datetime.timedelta(milliseconds=1)

    # Current balance = 300
    currencies = wallet.get_consumable_currency_balances(crypto)
    assert len(currencies) == 2
    assert currencies[0].quantity_left == 100
    assert currencies[1].quantity_left == 300
    assert tx_1.to_detail.get_last_consumable_balance().quantity_left == 100
    assert tx_2.to_detail.get_last_consumable_balance().quantity_left == 300

    currencies = wallet.get_consumable_currency_balances(crypto, quantity=50)
    assert len(currencies) == 1
    assert currencies[0].quantity_left == 100

    currencies = wallet.get_consumable_currency_balances(crypto, quantity=150)
    assert len(currencies) == 2
    assert currencies[0].quantity_left == 100
    assert currencies[1].quantity_left == 300


@pytest.mark.django_db()
def test_same_from_to_symbol():
    fiat = FiatCurrencyFactory.create(symbol="EUR")
    crypto = CryptoCurrencyFactory.create(symbol="BTC")

    wallet = WalletFactory.create(fiat=fiat)
    wallet_helper = WalletHelper(wallet)
    CurrencyPriceFactory.create(currency=crypto, fiat=fiat, date=wallet_helper.date(), price=1000)

    tx_1 = wallet_helper.deposit(crypto, 1000)
    tx_2 = wallet_helper.trade(crypto, 1000, crypto, 500)

    assert wallet.get_current_balance(crypto.symbol) == 500

    assert tx_1.to_detail.get_last_consumable_balance().quantity_left == 1000
    assert tx_2.to_detail.get_last_consumable_balance().quantity_left == 500
