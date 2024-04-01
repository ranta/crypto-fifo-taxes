import datetime
from decimal import Decimal

import pytest
from freezegun import freeze_time

from crypto_fifo_taxes.exceptions import SnapshotHelperException
from crypto_fifo_taxes.models import Currency, Snapshot, SnapshotBalance
from crypto_fifo_taxes.utils.helpers.snapshot_helper import BalanceDelta, SnapshotHelper
from tests.factories import CryptoCurrencyFactory, SnapshotBalanceFactory, TransactionFactory
from tests.utils import WalletHelper

pytestmark = [
    pytest.mark.django_db,
]

################
# Test Helpers #
################


def _get_snapshot_balance_for_date(
    date: datetime.date | datetime.datetime,
    currency: Currency,
) -> SnapshotBalance | None:
    if isinstance(date, datetime.datetime):
        date = date.date()

    return Snapshot.objects.get(date=date).balances.filter(currency=currency).first()


######################
# _get_starting_date #
######################


def test_snapshot_helper__starting_date__not_found():
    with pytest.raises(SnapshotHelperException):
        SnapshotHelper()


def test_snapshot_helper__starting_date__from_first_transaction():
    tx = TransactionFactory.create(timestamp=datetime.datetime(2020, 1, 1, 12))
    TransactionFactory.create(timestamp=datetime.datetime(2022, 2, 2, 12))

    snapshot_helper = SnapshotHelper()
    assert snapshot_helper.starting_date == tx.timestamp.date()


def test_snapshot_helper__starting_date__from_last_snapshot__no_balances():
    Snapshot.objects.create(date=datetime.date(2020, 1, 1))

    with pytest.raises(SnapshotHelperException):
        SnapshotHelper()


def test_snapshot_helper__starting_date__from_last_snapshot__no_transactions():
    SnapshotBalanceFactory.create(
        snapshot__date=datetime.date(2020, 1, 1),
        snapshot__cost_basis=1,
        currency__symbol="BTC",
        quantity=1,
    )

    with pytest.raises(SnapshotHelperException):
        SnapshotHelper()


def test_snapshot_helper__starting_date__from_last_snapshot__missing_snapshots_between_first_transaction():
    tx = TransactionFactory.create(timestamp=datetime.datetime(2020, 1, 1, 12))
    SnapshotBalanceFactory.create(
        snapshot__date=datetime.date(2020, 1, 10),
        snapshot__cost_basis=1,
        currency__symbol="BTC",
        quantity=1,
    )

    snapshot_helper = SnapshotHelper()
    assert snapshot_helper.starting_date == tx.timestamp.date()


def test_snapshot_helper__starting_date__from_last_snapshot__no_missing_snapshot_dates():
    TransactionFactory.create(timestamp=datetime.datetime(2020, 1, 1, 12))
    snapshot_balance = SnapshotBalanceFactory.create(
        snapshot__date=datetime.date(2020, 1, 1),
        snapshot__cost_basis=1,
        currency__symbol="BTC",
        quantity=1,
    )

    snapshot_helper = SnapshotHelper()
    assert snapshot_helper.starting_date == snapshot_balance.snapshot.date


######################
# generate_snapshots #
######################


@freeze_time("2020-01-31")
def test_snapshot_helper__generate_snapshots__count():
    TransactionFactory.create(timestamp=datetime.datetime(2020, 1, 1, 12))

    snapshot_helper = SnapshotHelper()
    assert snapshot_helper.total_days_to_generate == 31  # 1.1.2020 - 1.31.2020

    snapshot_helper.generate_snapshots()
    assert Snapshot.objects.all().count() == 31


######################################
# _process_single_transaction_detail #
######################################


def test_snapshot_helper___process_single_transaction_detail():
    btc = CryptoCurrencyFactory.create(symbol="BTC")

    wallet_helper = WalletHelper()
    tx_1 = wallet_helper.deposit(btc, 5, cost_basis=4)  # Value = 20
    tx_2 = wallet_helper.deposit(btc, 10, cost_basis=1)  # Value = 10
    tx_3 = wallet_helper.withdraw(btc, 2)  # Value does not matter

    snapshot_helper = SnapshotHelper()

    # btc_balance_delta gets updated in place
    btc_balance_delta = BalanceDelta(deposits=Decimal(0), withdrawals=Decimal(0), cost_basis=None)

    snapshot_helper._process_single_transaction_detail(tx_1.to_detail, btc_balance_delta)
    assert btc_balance_delta == BalanceDelta(deposits=5, cost_basis=4)  # 5*4 / 5 = 4

    snapshot_helper._process_single_transaction_detail(tx_2.to_detail, btc_balance_delta)
    assert btc_balance_delta == BalanceDelta(deposits=15, cost_basis=2)  # (5*4 + 10*1) / 15 = 2

    snapshot_helper._process_single_transaction_detail(tx_3.from_detail, btc_balance_delta)
    assert btc_balance_delta == BalanceDelta(deposits=15, cost_basis=2, withdrawals=2)


##########################################
# _generate_currency_delta_balance_table #
##########################################


def test_snapshot_helper__generate_currency_delta_balance_table():
    btc = CryptoCurrencyFactory.create(symbol="BTC")
    eth = CryptoCurrencyFactory.create(symbol="ETH")

    wallet_helper = WalletHelper()
    tx_1 = wallet_helper.deposit(btc, 5)

    wallet_helper.tx_time.next_day()
    tx_2 = wallet_helper.withdraw(btc, 2)

    wallet_helper.tx_time.next_day()
    tx_3 = wallet_helper.trade(btc, 3, eth, 15)
    wallet_helper.trade(eth, 5, btc, 1)

    snapshot_helper = SnapshotHelper()
    snapshot_helper._generate_currency_delta_balance_table()
    delta_table = snapshot_helper.balance_delta_table
    assert len(delta_table) == 3

    assert delta_table[tx_1.timestamp.date()][btc.id] == BalanceDelta(deposits=5, cost_basis=5)

    assert delta_table[tx_2.timestamp.date()][btc.id] == BalanceDelta(withdrawals=2)

    date_data = delta_table[tx_3.timestamp.date()]
    assert date_data[btc.id] == BalanceDelta(deposits=1, withdrawals=3, cost_basis=3)  # 3 BTC => 15 ETH
    assert date_data[eth.id] == BalanceDelta(deposits=15, withdrawals=5, cost_basis=Decimal("0.2"))  # 5 ETH => 1 BTC


def test_snapshot_helper__generate_currency_delta_balance_table__multiple_trades_on_same_day():
    eth = CryptoCurrencyFactory.create(symbol="ETH")
    ada = CryptoCurrencyFactory.create(symbol="ADA")

    wallet_helper = WalletHelper()
    tx_1 = wallet_helper.deposit(eth, 2)

    wallet_helper.tx_time.next_day()
    tx_2 = wallet_helper.trade(eth, Decimal("0.1"), ada, 10)
    wallet_helper.trade(eth, Decimal("0.2"), ada, 20)
    wallet_helper.trade(eth, Decimal("0.3"), ada, 30)
    wallet_helper.trade(eth, Decimal("0.4"), ada, 40)
    wallet_helper.trade(eth, Decimal("0.5"), ada, 50)

    snapshot_helper = SnapshotHelper()
    snapshot_helper._generate_currency_delta_balance_table()
    delta_table = snapshot_helper.balance_delta_table
    assert len(delta_table) == 2

    assert delta_table[tx_1.timestamp.date()][eth.id] == BalanceDelta(deposits=2, cost_basis=2)

    date_data = delta_table[tx_2.timestamp.date()]
    assert date_data[eth.id] == BalanceDelta(withdrawals=Decimal("1.5"))
    assert date_data[ada.id] == BalanceDelta(deposits=150, cost_basis=Decimal("0.01"))


##############################
# generate_snapshot_balances #
##############################


@freeze_time("2020-01-31")
def test_snapshot_helper__generate_snapshot_balances():
    btc = CryptoCurrencyFactory.create(symbol="BTC")
    eth = CryptoCurrencyFactory.create(symbol="ETH")

    wallet_helper = WalletHelper(start_time=datetime.datetime(2020, 1, 1))
    tx_1 = wallet_helper.deposit(btc, 5)

    wallet_helper.tx_time.next_day()
    tx_2 = wallet_helper.withdraw(btc, 2)

    wallet_helper.tx_time.next_day()
    tx_3 = wallet_helper.trade(btc, 3, eth, 15)
    wallet_helper.trade(eth, 5, btc, 1)

    snapshot_helper = SnapshotHelper()
    snapshot_helper.generate_snapshots()
    snapshot_helper.generate_snapshot_balances()

    balance = _get_snapshot_balance_for_date(tx_1.timestamp, btc)
    assert balance.quantity == 5
    assert balance.cost_basis == 5

    balance = _get_snapshot_balance_for_date(tx_2.timestamp, btc)
    assert balance.quantity == 3
    assert balance.cost_basis == 5

    balance = _get_snapshot_balance_for_date(tx_3.timestamp, btc)
    assert balance.quantity == 1
    assert balance.cost_basis == 5  # 5 ETH => 1 BTC
    balance = _get_snapshot_balance_for_date(tx_3.timestamp, eth)
    assert balance.quantity == 10
    assert balance.cost_basis == Decimal("0.2")  # 3 BTC => 15 ETH


@freeze_time("2020-01-31")
def test_snapshot_helper__generate_snapshot_balances__cost_basis():
    btc = CryptoCurrencyFactory.create(symbol="BTC")

    wallet_helper = WalletHelper(
        start_time=datetime.datetime(2020, 1, 1),
        increment=datetime.timedelta(days=1),
        auto_create_prices=False,
    )

    # Cost basis: 10
    tx_1 = wallet_helper.deposit(btc, 10, cost_basis=10)

    # Cost basis: (10*10 + 2*13) / 12 = 10.5
    tx_2 = wallet_helper.deposit(btc, 2, cost_basis=13)

    # Cost basis: (10*10 + 2*13 + 8*18) / 20 = 13.5
    tx_3 = wallet_helper.deposit(btc, 8, cost_basis=18)

    # Cost basis: (10*10 + 2*13 + 8*18 + 10*12) / 30 = 13
    tx_4 = wallet_helper.deposit(btc, 10, cost_basis=12)

    snapshot_helper = SnapshotHelper()
    snapshot_helper.generate_snapshots()
    snapshot_helper.generate_snapshot_balances()

    balance = _get_snapshot_balance_for_date(tx_1.timestamp, btc)
    assert balance.quantity == 10
    assert balance.cost_basis == 10

    balance = _get_snapshot_balance_for_date(tx_2.timestamp, btc)
    assert balance.quantity == 12
    assert balance.cost_basis == Decimal("10.5")

    balance = _get_snapshot_balance_for_date(tx_3.timestamp, btc)
    assert balance.quantity == 20
    assert balance.cost_basis == Decimal("13.5")

    balance = _get_snapshot_balance_for_date(tx_4.timestamp, btc)
    assert balance.quantity == 30
    assert balance.cost_basis == 13


# TODO: Test cost basis with trades and withdrawals
# TODO: Test `calculate_snapshots_worth`
