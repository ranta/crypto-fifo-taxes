import datetime
from decimal import Decimal

import pytest
from freezegun import freeze_time

from crypto_fifo_taxes.exceptions import SnapshotHelperException
from crypto_fifo_taxes.models import Snapshot
from crypto_fifo_taxes.utils.helpers.snapshot_helper import BalanceDelta, SnapshotHelper
from tests.factories import CryptoCurrencyFactory, SnapshotBalanceFactory, TransactionFactory
from tests.utils import WalletHelper

pytestmark = [
    pytest.mark.django_db,
]

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
    delta_table = snapshot_helper._generate_currency_delta_balance_table()
    assert len(delta_table) == 3

    assert delta_table[tx_1.timestamp.date()][btc.id] == BalanceDelta(deposits=5, cost_basis=5)

    assert delta_table[tx_2.timestamp.date()][btc.id] == BalanceDelta(withdrawals=2)

    date_data = delta_table[tx_3.timestamp.date()]
    assert date_data[btc.id] == BalanceDelta(deposits=1, withdrawals=3, cost_basis=3)  # 3 BTC => 15 ETH
    assert date_data[eth.id] == BalanceDelta(deposits=15, withdrawals=5, cost_basis=Decimal("0.2"))  # 5 ETH => 1 BTC


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

    snapshot_1_balances = Snapshot.objects.get(date=tx_1.timestamp.date()).get_balances()
    assert snapshot_1_balances == [{"currency_id": btc.id, "currency__symbol": "BTC", "quantity": 5, "cost_basis": 5}]

    snapshot_2_balances = Snapshot.objects.get(date=tx_2.timestamp.date()).get_balances()
    assert snapshot_2_balances == [{"currency_id": btc.id, "currency__symbol": "BTC", "quantity": 3, "cost_basis": 5}]

    snapshot_3_balances = Snapshot.objects.get(date=tx_3.timestamp.date()).get_balances()
    assert snapshot_3_balances[0] == {
        "currency_id": btc.id,
        "currency__symbol": "BTC",
        "quantity": 1,
        "cost_basis": Decimal("5"),  # 5 ETH => 1 BTC
    }
    assert snapshot_3_balances[1] == {
        "currency_id": eth.id,
        "currency__symbol": "ETH",
        "quantity": 10,
        "cost_basis": Decimal("0.2"),  # 3 BTC => 15 ETH
    }


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

    balances = Snapshot.objects.get(date=tx_1.timestamp.date()).get_balances()
    assert balances[0]["quantity"] == 10
    assert balances[0]["cost_basis"] == 10

    balances = Snapshot.objects.get(date=tx_2.timestamp.date()).get_balances()
    assert balances[0]["quantity"] == 12
    assert balances[0]["cost_basis"] == Decimal("10.5")

    balances = Snapshot.objects.get(date=tx_3.timestamp.date()).get_balances()
    assert balances[0]["quantity"] == 20
    assert balances[0]["cost_basis"] == Decimal("13.5")

    balances = Snapshot.objects.get(date=tx_4.timestamp.date()).get_balances()
    assert balances[0]["quantity"] == 30
    assert balances[0]["cost_basis"] == 13


# TODO: Test cost basis with trades and withdrawals
# TODO: Test `calculate_snapshots_worth`
