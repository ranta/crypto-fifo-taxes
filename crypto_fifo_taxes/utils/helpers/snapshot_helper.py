import datetime
import logging
import sys
from copy import copy
from dataclasses import dataclass
from decimal import Decimal
from typing import Annotated

from django.db.models import F, Q, QuerySet, Sum

from crypto_fifo_taxes.enums import TransactionLabel, TransactionType
from crypto_fifo_taxes.exceptions import MissingPriceHistoryError, SnapshotHelperException
from crypto_fifo_taxes.models import Snapshot, SnapshotBalance, Transaction, TransactionDetail
from crypto_fifo_taxes.utils.common import log_progress
from crypto_fifo_taxes.utils.currency import get_currency
from crypto_fifo_taxes.utils.date_utils import utc_date, utc_end_of_day, utc_start_of_day
from crypto_fifo_taxes.utils.db import CoalesceZero

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

type CurrencyID = Annotated[int, "currency_id"]


@dataclass
class BalanceDelta:
    deposits: Decimal
    withdrawals: Decimal
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


class SnapshotHelper:
    """
    Helper class for generating snapshots and snapshot balances.

    Usage:
    >>> helper = SnapshotHelper()
    >>> helper.generate_snapshots()
    >>> helper.generate_snapshot_balances()
    >>> helper.calculate_snapshots_worth()
    """

    starting_date: datetime.date
    today: datetime.date
    total_days_to_generate: int
    selected_snapshots_qs: QuerySet[Snapshot]

    def __init__(self) -> None:
        self.starting_date = self._get_starting_date()
        self.today = utc_date()
        self.total_days_to_generate = (self.today - self.starting_date).days + 1  # Inclusive
        self.selected_snapshots_qs = Snapshot.objects.filter(date__gte=self.starting_date).order_by("date")

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

    def generate_snapshots(self) -> None:
        """Generate snapshots (without balances) for each day starting from the first transaction date. until today."""
        logger.info(f"Creating empty snapshots starting from {self.starting_date}")

        # Delete any existing snapshots from the period about to be generated
        self.selected_snapshots_qs.delete()

        snapshots = []
        for date_index in range(self.total_days_to_generate):
            snapshot_date = self.starting_date + datetime.timedelta(days=date_index)
            snapshots.append(Snapshot(date=snapshot_date))

        Snapshot.objects.bulk_create(snapshots)

        logger.info("Created empty snapshots!")

    def _process_single_transaction_detail(self, transaction_detail: TransactionDetail, day_data: BalanceDelta) -> None:
        """Process a single transaction detail and update the day's data."""
        # Incoming
        if hasattr(transaction_detail, "to_detail"):
            if day_data.deposits == 0:
                day_data.deposits = transaction_detail.quantity
                day_data.cost_basis = transaction_detail.cost_basis
            else:
                total_value = day_data.deposits_value + transaction_detail.total_value
                total_quantity = day_data.deposits + transaction_detail.quantity

                day_data.deposits = total_value
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

    def _generate_currency_delta_balance_table(self) -> dict[datetime.date, dict[CurrencyID, BalanceDelta]]:
        """Generate a table of the changes in currency balances for each day."""
        logger.info("Generating snapshots currency balances...")

        transaction_details = TransactionDetail.objects.filter(
            tx_timestamp__gte=utc_start_of_day(self.starting_date),
        ).order_by("tx_timestamp")
        transaction_details_count = len(transaction_details)

        table: dict[datetime.date, dict[CurrencyID, BalanceDelta]] = {}

        for i, transaction_detail in enumerate(transaction_details):
            date: datetime.date = transaction_detail.transaction.timestamp.date()
            currency_id: int = transaction_detail.currency_id

            # Empty defaults
            if date not in table:
                table[date] = {}
            if currency_id not in table[date]:
                table[date][currency_id] = BalanceDelta(deposits=Decimal(0), withdrawals=Decimal(0), cost_basis=None)

            self._process_single_transaction_detail(transaction_detail, table[date][currency_id])

            log_progress(f"Processing balances: {date}", i, transaction_details_count, 200)

        return table

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

    def generate_snapshot_balances(self) -> None:
        """Generate snapshot balances for each day in the period."""
        logger.info("Creating SnapshotBalance objects...")

        table = self._generate_currency_delta_balance_table()

        # Map snapshots to their date for easy access
        snapshot_to_date: dict[datetime.date, Snapshot] = {
            snapshot.date: snapshot for snapshot in self.selected_snapshots_qs
        }

        # List of SnapshotBalance objects to be bulk created
        snapshot_balances: list[SnapshotBalance] = []

        # Last known balance for each currency
        latest_balances: dict[CurrencyID, SnapshotBalance] = {}

        # Process snapshots
        for current_date, table_currencies in table.items():
            snapshot: Snapshot = snapshot_to_date.get(current_date)
            if snapshot is None:
                raise SnapshotHelperException(f"Snapshot not found for date {current_date}")

            # Process single currency balance for the snapshot
            for currency_id, balance_delta in table_currencies.items():
                # Empty defaults
                if currency_id not in latest_balances:
                    latest_balances[currency_id] = SnapshotBalance(
                        currency_id=currency_id,
                        quantity=Decimal(0),
                        cost_basis=Decimal(0),
                    )
                latest_balance: SnapshotBalance = latest_balances[currency_id]

                self._process_single_date_currency(balance_delta, latest_balance)

                # Skip empty balances
                if balance_delta.withdrawals == 0 and latest_balance.quantity == 0:
                    continue

                latest_balance.snapshot = snapshot
                # Append a copy of the latest balance to the list (to avoid updating the same object later)
                snapshot_balances.append(copy(latest_balance))

        SnapshotBalance.objects.bulk_create(snapshot_balances)
        logger.info("Generated snapshot balances complete!")

    def calculate_snapshots_worth(self) -> None:
        self.selected_snapshots_qs.update(worth=None, cost_basis=None, deposits=None)

        for snapshot in self.selected_snapshots_qs:
            self._calculate_snapshot_worth(snapshot)

        logger.info("Calculating snapshots worth complete!")

    def _calculate_snapshot_worth(self, snapshot: Snapshot) -> None:
        logger.info(f"Calculating snapshot worth. {snapshot.date}")

        sum_worth = Decimal(0)
        sum_cost_basis = Decimal(0)

        balances = snapshot.get_balances()
        for balance in balances:
            if balance["quantity"] == 0:
                continue

            currency = get_currency(balance["currency_id"])
            # For FIAT currencies we can simply add then, as their worth is their quantity
            if currency.is_fiat:
                sum_worth += balance["quantity"]
                sum_cost_basis += balance["cost_basis"]
                continue

            # For non-FIAT currencies we need to fetch their price
            try:
                currency_price = currency.get_fiat_price(date=snapshot.date)
            # If the price is missing, we skip the currency and add its cost basis to the sums
            except MissingPriceHistoryError:
                logger.exception(f"Missing price for currency {currency}")

                sum_worth += balance["cost_basis"]
                sum_cost_basis += balance["cost_basis"]
                continue

            if currency_price is None:
                continue

            sum_worth += balance["quantity"] * currency_price.price
            sum_cost_basis += balance["quantity"] * balance["cost_basis"]

        # This defines what transactions are deposits
        deposits_filter = Q(
            Q(tx_timestamp__lte=utc_end_of_day(snapshot.date))
            & Q(to_detail__isnull=False)
            & Q(from_detail__isnull=True)
            & Q(
                Q(currency__symbol="EUR") & Q(to_detail__transaction_type=TransactionType.DEPOSIT)
                | Q(to_detail__transaction_label=TransactionLabel.MINING)
            )
        )

        deposits = Decimal(0)
        last_snapshot = Snapshot.objects.filter(date__lt=snapshot.date).order_by("-date").first()
        if last_snapshot is None:
            # First snapshot; Simply take all predating deposits
            deposits_qs = TransactionDetail.objects.filter(deposits_filter)
        else:
            # n:th snapshot; Sum deposits of last snapshot to the deposits in period between this and last snapshot
            deposits += last_snapshot.deposits
            deposits_filter &= Q(
                tx_timestamp__gt=datetime.datetime.combine(last_snapshot.date, datetime.time.max, tzinfo=datetime.UTC)
            )
            deposits_qs = TransactionDetail.objects.filter(deposits_filter)
        deposits += deposits_qs.annotate(worth=CoalesceZero(F("quantity") * F("cost_basis"))).aggregate(
            sum_deposits_worth=Sum("worth")
        )["sum_deposits_worth"] or Decimal(0)

        snapshot.worth = sum_worth
        snapshot.cost_basis = sum_cost_basis
        snapshot.deposits = deposits
        snapshot.save()
