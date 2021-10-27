from datetime import datetime, time, timedelta

import pytz
from django.contrib.auth.models import User
from django.core.management import BaseCommand
from django.utils import timezone

from crypto_fifo_taxes.models import Snapshot, SnapshotBalance, Transaction, TransactionDetail


class Command(BaseCommand):
    user = User.objects.first()
    first_date = Transaction.objects.order_by("timestamp").first().timestamp.date()

    def add_arguments(self, parser):
        parser.add_argument("-m", "--mode", type=int, help="Mode this command will be run in. 0=fast, 1=full")

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

    def generate_snapshots(self) -> None:
        today = timezone.now().date()
        day_delta = 0

        while True:
            date = self.first_date + timedelta(days=day_delta)
            if date >= today:
                break
            print(date)

            snapshot, __ = Snapshot.objects.get_or_create(user=self.user, date=date)
            self.generate_snapshot_currencies(snapshot=snapshot, date=date)
            snapshot.calculate_worth()

            day_delta += 1

    def handle(self, *args, **kwargs):
        sync_start_time = datetime.now()
        self.mode = kwargs.pop("mode", 0)

        # Delete all old snapshots, if this command is being run some if it is most likely outdated :)
        Snapshot.objects.all().delete()

        self.generate_snapshots()

        print(f"Total time elapsed: {datetime.now() - sync_start_time}")