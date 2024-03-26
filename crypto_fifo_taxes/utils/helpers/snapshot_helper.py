import datetime
import logging
import sys
from dataclasses import dataclass
from decimal import Decimal
from typing import Annotated

import pytz
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import F, Q, Sum

from crypto_fifo_taxes.enums import TransactionLabel, TransactionType
from crypto_fifo_taxes.exceptions import MissingPriceHistoryError
from crypto_fifo_taxes.models import Snapshot, SnapshotBalance, Transaction, TransactionDetail
from crypto_fifo_taxes.utils.currency import get_currency
from crypto_fifo_taxes.utils.date_utils import utc_date, utc_end_of_day, utc_start_of_day
from crypto_fifo_taxes.utils.db import CoalesceZero

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BalanceDelta:
    quantity: Decimal
    cost_basis: Decimal

    @property
    def value(self) -> Decimal:
        return self.quantity * self.cost_basis


class SnapshotHelper:
    user: User
    starting_date: datetime.date
    today: datetime.date
    total_days_to_generate: int

    def __init__(self) -> None:
        self.user = User.objects.first()
        self.starting_date = self._get_starting_date()
        self._validate_starting_date(self.starting_date)

        self.today = utc_date()
        self.total_days_to_generate = (self.today - self.starting_date).days

    def _get_starting_date(self) -> datetime.date:
        latest_snapshot_date = (
            Snapshot.objects.filter(balances__isnull=False, cost_basis__isnull=False)
            .order_by("-date")
            .values_list("date", flat=True)
            .first()
        )
        if latest_snapshot_date is not None:
            return latest_snapshot_date

        first_transaction_date = Transaction.objects.order_by("timestamp").first().timestamp.date()
        if first_transaction_date is None:
            raise ValueError("Starting date not found, no transactions found.")

        return first_transaction_date

    @staticmethod
    def _validate_starting_date(starting_date) -> None:
        first_transaction_date = Transaction.objects.order_by("timestamp").first().timestamp.date()

        past_snapshots_count = Snapshot.objects.filter(date__lte=starting_date).count()
        required_snapshots_count = (starting_date - first_transaction_date).days

        if required_snapshots_count > past_snapshots_count:
            raise ValidationError("Snapshots are missing for a date before given date. Unable to continue.")

    def _generate_snapshot_currencies(self, snapshot: Snapshot) -> list[SnapshotBalance]:
        timestamp_from = utc_start_of_day(snapshot.date)
        timestamp_to = utc_end_of_day(snapshot.date)

        balance_deltas = TransactionDetail.objects.get_balances_for_snapshot(timestamp_from, timestamp_to)

        snapshot_balances = []
        for delta in balance_deltas:
            new_quantity = delta["new_balance"]
            cost_basis = delta["new_cost_basis"]

            snapshot_balances.append(
                SnapshotBalance(
                    snapshot=snapshot,
                    currency_id=delta["currency_id"],
                    quantity=new_quantity,
                    cost_basis=cost_basis,
                )
            )
        return snapshot_balances

    def _get_percentage_str(self, v1: int, v2) -> str:
        return f"{(v1) / v2 * 100:>5.2f}%"

    def generate_snapshots(self) -> None:
        logger.info(f"Creating empty snapshots starting from {self.starting_date}")
        Snapshot.objects.filter(date__gte=self.starting_date).delete()

        snapshots = []
        for date_index in range(self.total_days_to_generate + 1):
            current_date = self.starting_date + datetime.timedelta(days=date_index)
            snapshot = Snapshot(user=self.user, date=current_date)
            snapshots.append(snapshot)

        Snapshot.objects.bulk_create(snapshots)
        logger.info("Created empty snapshots!")

    def generate_snapshot_balances(self) -> None:
        logger.info("Generating snapshots currency balances...")
        table: dict[datetime.date, dict[Annotated[int, "currency_id"], BalanceDelta]] = {}
        td_queryset = TransactionDetail.objects.filter(
            tx_timestamp__gte=utc_start_of_day(self.starting_date),
            tx_timestamp__lte=utc_end_of_day(self.today),
        ).order_by("tx_timestamp")

        # Create the table with deltas for each currency on each day
        for i, td in enumerate(td_queryset):
            date = td.tx_timestamp.date()
            # Empty defaults
            if date not in table:
                table[date] = {}
            if td.currency.symbol not in table[date]:
                table[date][td.currency_id] = BalanceDelta(quantity=Decimal(0), cost_basis=Decimal(0))

            # Incoming
            if hasattr(td, "to_detail"):
                table[date][td.currency_id].quantity += td.quantity
            # Outgoing
            elif (
                hasattr(td, "from_detail")
                # Is fee and not an actual withdrawal
                # In withdrawals the fee is included in from_detail quantity, and deducted from the total received
                or (hasattr(td, "fee_detail") and td.fee_detail.transaction_type != TransactionType.WITHDRAW)
            ):
                table[date][td.currency_id].quantity -= td.quantity

            if i % 200 == 0:
                logger.info(f"Processing balances: {self._get_percentage_str(i, len(td_queryset))}")

        logger.info("Creating SnapshotBalance objects...")
        snapshots = Snapshot.objects.filter(date__gte=self.starting_date).order_by("date")
        snapshot_to_date: dict[datetime.date, Snapshot] = {snapshot.date: snapshot for snapshot in snapshots}
        snapshot_balances: list[SnapshotBalance] = []
        last_balance: dict[Annotated[int, "currency_id"], BalanceDelta] = {}

        for current_date, currencies in table.items():
            snapshot: Snapshot = snapshot_to_date.get(current_date)
            if snapshot is None:
                raise ValueError(f"Snapshot not found for date {current_date}")

            for currency_id, balance_delta in currencies.items():
                if currency_id not in last_balance:
                    last_balance[currency_id] = BalanceDelta(quantity=Decimal(0), cost_basis=Decimal(0))

                # Quantity
                last_balance[currency_id].quantity += balance_delta.quantity

                # Cost Basis
                # Balance emptied or no last known cost basis
                if last_balance[currency_id].quantity == 0 or last_balance[currency_id].cost_basis == 0:
                    last_balance[currency_id].cost_basis += balance_delta.cost_basis
                # Negative delta, cost basis should not be changed from the last known value
                elif balance_delta.quantity < 0:
                    pass
                # Calculate new cost basis weighted by quantity
                else:
                    total_value = last_balance[currency_id].value + balance_delta.value
                    last_balance[currency_id].cost_basis = total_value / last_balance[currency_id].quantity

                snapshot_balances.append(
                    SnapshotBalance(
                        snapshot=snapshot,
                        currency_id=currency_id,
                        quantity=last_balance[currency_id].quantity,
                        cost_basis=last_balance[currency_id].cost_basis,
                    )
                )

        SnapshotBalance.objects.bulk_create(snapshot_balances)
        logger.info("Generated snapshot balances complete!")

    def calculate_snapshots_worth(self) -> None:
        Snapshot.objects.filter(date__gte=self.starting_date).update(worth=None, cost_basis=None, deposits=None)

        qs = Snapshot.objects.filter(date__gte=self.starting_date)
        for snapshot in qs:
            self._calculate_snapshot_worth(snapshot)

        logger.info("Calculating snapshots worth complete!")

    @staticmethod
    def _calculate_snapshot_worth(snapshot: Snapshot) -> None:
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
                tx_timestamp__gt=datetime.datetime.combine(last_snapshot.date, datetime.time.max, tzinfo=pytz.UTC)
            )
            deposits_qs = TransactionDetail.objects.filter(deposits_filter)
        deposits += deposits_qs.annotate(worth=CoalesceZero(F("quantity") * F("cost_basis"))).aggregate(
            sum_deposits_worth=Sum("worth")
        )["sum_deposits_worth"] or Decimal(0)

        snapshot.worth = sum_worth
        snapshot.cost_basis = sum_cost_basis
        snapshot.deposits = deposits
        snapshot.save()
