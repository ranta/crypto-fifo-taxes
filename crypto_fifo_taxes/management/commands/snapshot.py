from datetime import date, datetime, time, timedelta

import pytz
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import BaseCommand
from django.utils import timezone

from crypto_fifo_taxes.models import Snapshot, SnapshotBalance, Transaction, TransactionDetail
from crypto_fifo_taxes.utils.wrappers import print_time_elapsed


class Command(BaseCommand):
    user = User.objects.first()
    first_date = None

    def add_arguments(self, parser):
        parser.add_argument("-m", "--mode", type=int, help="Mode this command will be run in. 0=fast, 1=full")
        parser.add_argument("-d", "--date", type=str, help="Start from this date. Format: YYYY-MM-DD")

    def generate_snapshot_currencies(self, snapshot: Snapshot, date: datetime.date) -> None:
        timestamp_from = datetime.combine(date, time(0, 0, 0), tzinfo=pytz.UTC)
        timestamp_to = datetime.combine(date, time(23, 59, 59), tzinfo=pytz.UTC)

        balance_deltas = TransactionDetail.objects.filter(
            tx_timestamp__gte=timestamp_from,
            tx_timestamp__lte=timestamp_to,
        ).get_balances_for_snapshot()

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
        SnapshotBalance.objects.bulk_create(snapshot_balances)

    @print_time_elapsed
    def generate_snapshots(self) -> None:
        print()  # Newline for prettier formatting
        today = timezone.now().date()
        day_delta = 0
        total_days = (today - self.date).days

        while True:
            date = self.date + timedelta(days=day_delta)
            if date >= today:
                break

            snapshot, created = Snapshot.objects.get_or_create(user=self.user, date=date)
            if not created:
                # Delete old balances for snapshot when updating snapshot
                snapshot.balances.all().delete()
            self.generate_snapshot_currencies(snapshot=snapshot, date=date)
            snapshot.calculate_worth()

            day_delta += 1
            print(f"Calculating snapshots. {(day_delta + 1) / total_days * 100:>5.2f}% ({date})", end="\r")

    def validate_starting_date(self, first_transaction_date: date, starting_date: date) -> None:
        """
        Validate that snapshots exist for all days between the first transaction and given starting date
        """
        past_snapshots_count = Snapshot.objects.filter(date__lte=starting_date).count()
        required_snapshots_count = (starting_date - first_transaction_date).days
        if required_snapshots_count > past_snapshots_count:
            raise ValidationError("Snapshots are missing for a date before given date. Unable to continue.")

    def get_starting_date(self) -> None:
        first_transaction_date = Transaction.objects.order_by("timestamp").first().timestamp.date()

        # Start from specific date
        if self.date is not None:
            starting_date = datetime.strptime(self.date, "%Y-%m-%d").date()
            self.validate_starting_date(first_transaction_date=first_transaction_date, starting_date=starting_date)
            self.date = starting_date
            return

        # Fast mode (Continue from latest snapshot)
        if not self.mode and Snapshot.objects.exists():  # Fast mode is usable only if any previous snapshots exist
            latest_snapshot_date = Snapshot.objects.order_by("-date").values_list("date", flat=True).first()
            if latest_snapshot_date is not None:
                self.validate_starting_date(first_transaction_date, latest_snapshot_date)
                self.date = latest_snapshot_date
                return

        # Full mode
        self.date = first_transaction_date

    def handle(self, *args, **kwargs):
        self.mode = kwargs.pop("mode", None)
        self.date = kwargs.pop("date", None)

        self.get_starting_date()
        self.generate_snapshots()
