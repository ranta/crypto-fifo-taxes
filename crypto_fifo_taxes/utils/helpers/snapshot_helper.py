import datetime
import logging
import sys
from collections import defaultdict
from copy import copy
from dataclasses import dataclass
from decimal import Decimal
from typing import Annotated

from django.db.models import F, Q, QuerySet, Sum

from crypto_fifo_taxes.enums import TransactionLabel, TransactionType
from crypto_fifo_taxes.exceptions import MissingPriceHistoryError, SnapshotHelperException
from crypto_fifo_taxes.models import Currency, CurrencyPrice, Snapshot, SnapshotBalance, Transaction, TransactionDetail
from crypto_fifo_taxes.utils.common import log_progress
from crypto_fifo_taxes.utils.currency import get_currency
from crypto_fifo_taxes.utils.date_utils import utc_date, utc_end_of_day
from crypto_fifo_taxes.utils.db import CoalesceZero

__all__ = [
    "BalanceDelta",
    "SnapshotHelper",
]

from crypto_fifo_taxes.utils.wrappers import print_entry_and_exit

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

type CurrencyID = Annotated[int, "currency_id"]


@dataclass
class BalanceDelta:
    deposits: Decimal  # All transactions that increase the balance of a currency.
    withdrawals: Decimal  # All transactions that decrease the balance of a currency.
    cost_basis: Decimal | None  # Average cost basis for all "deposit" transactions in the day, weighted by quantity

    def __init__(
        self,
        deposits: Decimal | int = Decimal(),
        withdrawals: Decimal | int = Decimal(),
        cost_basis: Decimal | int | None = None,
    ):
        self.deposits = Decimal(deposits)
        self.withdrawals = Decimal(withdrawals)
        self.cost_basis = Decimal(cost_basis) if cost_basis is not None else None

    def __eq__(self, other: "BalanceDelta"):
        return (
            self.deposits == other.deposits
            and self.withdrawals == other.withdrawals
            and self.cost_basis == other.cost_basis
        )

    @property
    def deposits_value(self) -> Decimal:
        return self.deposits * self.cost_basis


########################################################################################################################


class MassCurrencyPriceHelper:
    """Prefetch and cache currency prices for a given period."""

    price_dict: dict[CurrencyID, dict[datetime.date, Decimal]]

    def __init__(self):
        super().__init__()
        self.price_dict = {}

    def get_price(self, currency: Currency, date: datetime.date) -> Decimal:
        if currency.pk not in self.price_dict:
            self.price_dict[currency.pk] = dict(
                CurrencyPrice.objects.filter(
                    currency=currency,
                    date__gte=date,
                ).values_list("date", "price")
            )

        price = self.price_dict[currency.pk].get(date)
        if price is None:
            return currency.get_fiat_price(date).price

        return price


########################################################################################################################


class SnapshotGeneratorHelperMixin:
    starting_date: datetime.date
    total_days_to_generate: int
    selected_snapshots_qs: QuerySet[Snapshot]

    @print_entry_and_exit(logger=logger, function_name="Generate Empty Snapshots")
    def generate_snapshots(self) -> None:
        """Generate snapshots (without balances) for each day from the first transaction date until today."""
        # Delete any existing snapshots from the period about to be generated
        self.selected_snapshots_qs.delete()

        snapshots = []
        for date_index in range(self.total_days_to_generate):
            snapshot_date = self.starting_date + datetime.timedelta(days=date_index)
            snapshots.append(Snapshot(date=snapshot_date))

        Snapshot.objects.bulk_create(snapshots)


########################################################################################################################


class SnapshotBalanceHelperMixin:
    starting_date: datetime.date
    selected_snapshots_qs: QuerySet[Snapshot]
    balance_delta_table: defaultdict[datetime.date, defaultdict[CurrencyID, BalanceDelta]]

    def __init__(self):
        self.balance_delta_table = defaultdict(
            lambda: defaultdict(
                lambda: BalanceDelta(deposits=Decimal(0), withdrawals=Decimal(0), cost_basis=None),
            )
        )

    @print_entry_and_exit(logger=logger, function_name="Generate Snapshot Balances")
    def generate_snapshot_balances(self) -> None:
        """
        Generate snapshot balances for each day in the period.

        > generate_snapshot_balances
            > _generate_currency_delta_balance_table
                > _process_single_transaction_detail
            > _generate_snapshot_balances
                > _process_single_date_currency
        """
        self._generate_currency_delta_balance_table()

        snapshot_balances: list[SnapshotBalance] = self._generate_snapshot_balances()

        SnapshotBalance.objects.bulk_create(snapshot_balances)

    def _generate_currency_delta_balance_table(self):
        """
        Generate a table of the changes in currency balances for each day.

        Loop through all transaction details, and aggregate their changes in the `self.balance_delta_table`.
        """
        transaction_details = TransactionDetail.objects.order_by_timestamp().filter(
            tx_timestamp__date__gte=self.starting_date
        )
        for i, transaction_detail in enumerate(transaction_details):
            date: datetime.date = transaction_detail.transaction.timestamp.date()
            currency_id: int = transaction_detail.currency_id

            log_progress(logger, f"Processing balances table: {date}", i, len(transaction_details), 1000)

            table_entry: BalanceDelta = self.balance_delta_table[date][currency_id]
            self._process_single_transaction_detail(transaction_detail=transaction_detail, day_data=table_entry)

    def _process_single_transaction_detail(self, transaction_detail: TransactionDetail, day_data: BalanceDelta) -> None:
        """Process a single transaction detail and update the day's data."""
        # Incoming
        if hasattr(transaction_detail, "to_detail"):
            # No deposits yet, set the first deposit
            if day_data.deposits == 0:
                day_data.deposits = transaction_detail.quantity
                day_data.cost_basis = transaction_detail.cost_basis
            # Add to the existing deposits
            else:
                total_value = day_data.deposits_value + transaction_detail.total_value
                total_quantity = day_data.deposits + transaction_detail.quantity

                day_data.deposits = total_quantity
                day_data.cost_basis = total_value / total_quantity

        # Outgoing
        elif (
            hasattr(transaction_detail, "from_detail")
            # Is fee and not a withdrawal.
            # In withdrawals the fee is included in from_detail quantity, and deducted from the total received
            or (
                hasattr(transaction_detail, "fee_detail")
                and transaction_detail.fee_detail.transaction_type != TransactionType.WITHDRAW
            )
        ):
            day_data.withdrawals += transaction_detail.quantity

    def _generate_snapshot_balances(self) -> list[SnapshotBalance]:
        # List of SnapshotBalance objects to be bulk created
        snapshot_balances: list[SnapshotBalance] = []

        # Last known balance for each currency ({currency_id: SnapshotBalance})
        latest_balances: defaultdict[CurrencyID, SnapshotBalance] = defaultdict(
            lambda: SnapshotBalance(
                currency_id=currency_id,
                quantity=Decimal(0),
                cost_basis=Decimal(0),
            )
        )

        # Generate SnapshotBalances
        for snapshot in self.selected_snapshots_qs:
            table_currencies = self.balance_delta_table[snapshot.date]

            # Process single currency balance for the snapshot
            for currency_id, balance_delta in table_currencies.items():
                try:
                    self._process_single_date_currency(balance_delta, latest_balances[currency_id])
                except SnapshotHelperException:
                    logger.exception(f"Error processing currency {get_currency(currency_id)} on {snapshot.date}")
                    raise

            # Add SnapshotBalance for each currency to the list
            for currency_id in list(latest_balances.keys()):  # Copy the keys to avoid changing the dict while iterating
                # Delete the currency from the latest balances if it's empty
                if latest_balances[currency_id].quantity == 0:
                    del latest_balances[currency_id]
                    # print("deleted:", get_currency(currency_id), snapshot.date)
                    continue

                # Append a copy of the latest balance to the list (to avoid updating the same object later)
                latest_balances[currency_id].snapshot = snapshot
                snapshot_balances.append(copy(latest_balances[currency_id]))

        return snapshot_balances

    def _process_single_date_currency(self, balance_delta: BalanceDelta, latest_balance: SnapshotBalance) -> None:
        # Cost Basis
        # Balance was empty or no last known cost basis
        if not latest_balance.quantity or not latest_balance.cost_basis:
            latest_balance.cost_basis = balance_delta.cost_basis
        # Negative delta, cost basis should not be changed from the last known value
        elif balance_delta.deposits - balance_delta.withdrawals < 0:
            pass
        # Calculate new cost basis weighted by quantity
        else:
            # TODO: This is wrong, this way we only get the average cost basis, not the real cost basis.
            #  To get the real cost basis we first need to get all deposits and withdrawals in history...
            total_value = latest_balance.total_value + balance_delta.deposits_value
            latest_balance.cost_basis = total_value / (latest_balance.quantity + balance_delta.deposits)

        # Quantity
        latest_balance.quantity += balance_delta.deposits - balance_delta.withdrawals

        if latest_balance.quantity < 0:
            raise SnapshotHelperException(f"Negative balance for currency {get_currency(latest_balance.currency_id)}")


########################################################################################################################


class SnapshotWorthHelperMixin:
    total_days_to_generate: int
    selected_snapshots_qs: QuerySet[Snapshot]
    mass_price_helper: MassCurrencyPriceHelper

    @print_entry_and_exit(logger=logger, function_name="Calculate Snapshots Worth")
    def calculate_snapshots_worth(self) -> None:
        self.mass_price_helper = MassCurrencyPriceHelper()

        self.selected_snapshots_qs.update(worth=None, cost_basis=None, deposits=None)

        snapshot_qs = self.selected_snapshots_qs.prefetch_related("balances", "balances__currency")
        for i, snapshot in enumerate(snapshot_qs):
            log_progress(logger, f"Calculating snapshot worth: {snapshot.date}", i, self.total_days_to_generate, 100)
            self._calculate_snapshot_worth(snapshot)

    def _calculate_snapshot_worth(self, snapshot: Snapshot) -> None:
        sum_worth = Decimal(0)
        sum_cost_basis = Decimal(0)

        for balance in snapshot.balances.all():
            if balance.quantity == 0:
                continue

            # For FIAT currencies we can simply add then, as their worth is their quantity
            if balance.currency.is_fiat:
                sum_worth += balance.quantity
                sum_cost_basis += balance.cost_basis
                continue

            # For non-FIAT currencies we need to fetch their price
            try:
                currency_price: Decimal = self.mass_price_helper.get_price(balance.currency, snapshot.date)
            # If the price is missing, we skip the currency and add its cost basis to the sums
            except MissingPriceHistoryError:
                logger.debug(f"Missing price for currency {balance.currency}")

                sum_worth += balance.cost_basis
                sum_cost_basis += balance.cost_basis
                continue

            if not currency_price:
                continue

            sum_worth += balance.quantity * currency_price
            sum_cost_basis += balance.quantity * balance.cost_basis

        # This defines what transactions are deposits
        deposits_filter = Q(
            Q(to_detail__isnull=False)
            & Q(to_detail__timestamp__lte=utc_end_of_day(snapshot.date))
            & Q(from_detail__isnull=True)
            & Q(
                Q(currency__symbol="EUR") & Q(to_detail__transaction_type=TransactionType.DEPOSIT)
                | Q(to_detail__transaction_label=TransactionLabel.MINING)
            )
        )

        deposits = Decimal(0)
        last_snapshot = Snapshot.objects.filter(date__lt=snapshot.date).order_by("-date").first()
        if last_snapshot is not None:
            deposits += last_snapshot.deposits
            deposits_filter &= Q(to_detail__timestamp__gt=utc_end_of_day(last_snapshot.date))

        deposits_qs = TransactionDetail.objects.filter(deposits_filter).order_by("to_detail__timestamp")

        deposits += deposits_qs.annotate(
            worth=CoalesceZero(F("quantity") * F("cost_basis")),
        ).aggregate(sum_deposits_worth=Sum("worth"))["sum_deposits_worth"] or Decimal(0)

        snapshot.worth = sum_worth
        snapshot.cost_basis = sum_cost_basis
        snapshot.deposits = deposits
        snapshot.save()


########################################################################################################################


class SnapshotHelper(SnapshotGeneratorHelperMixin, SnapshotBalanceHelperMixin, SnapshotWorthHelperMixin):
    """
    Helper class for generating snapshots and snapshot balances.

    Usage:
    >>> helper = SnapshotHelper()
    >>> helper.generate_snapshots()
    >>> helper.generate_snapshot_balances()
    >>> helper.calculate_snapshots_worth()
    """

    starting_date: datetime.date
    total_days_to_generate: int
    selected_snapshots_qs: QuerySet[Snapshot]

    def __init__(self) -> None:
        super().__init__()
        self.starting_date = self._get_starting_date()
        today = utc_date()
        self.total_days_to_generate = (today - self.starting_date).days + 1  # Inclusive
        self.selected_snapshots_qs = Snapshot.objects.filter(date__gte=self.starting_date).order_by("date")

        logger.info(f"SnapshotHelper initialised with Starting Date={self.starting_date}")

    def _get_starting_date(self) -> datetime.date:
        first_tx_date = Transaction.objects.order_by("timestamp").values_list("timestamp__date", flat=True).first()

        if first_tx_date is None:
            raise SnapshotHelperException("No transactions founds.")

        latest_snapshot_date = (
            Snapshot.objects.filter(balances__isnull=False, cost_basis__isnull=False)
            .order_by("-date")
            .values_list("date", flat=True)
            .first()
        )

        # If no snapshots are found, return the date of the first transaction
        if latest_snapshot_date is None:
            return first_tx_date
        else:
            # Check if there are missing snapshots between the first transaction and the latest snapshot
            past_snapshots_count = Snapshot.objects.filter(date__lte=latest_snapshot_date).count()
            required_snapshots_count = (latest_snapshot_date - first_tx_date).days

            # Return the latest snapshot date if all snapshots are found
            if required_snapshots_count <= past_snapshots_count:
                return latest_snapshot_date
            else:
                return first_tx_date
