from datetime import datetime

from django.core.management import BaseCommand
from django.db.models import Q, QuerySet

from crypto_fifo_taxes.models import Transaction
from crypto_fifo_taxes.utils.wrappers import print_time_elapsed


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--fast", type=int)
        parser.add_argument("-d", "--date", type=str, help="Start from this date. Format: YYYY-MM-DD")

    @staticmethod
    @print_time_elapsed
    def calculate_cost_bases(transactions: QuerySet[Transaction]):
        count = transactions.count()
        for i, t in enumerate(transactions):
            print(f"Calculating cost bases. {(i + 1) / count * 100:>5.2f}% ({t.timestamp.date()})", end="\r")
            t.fill_cost_basis()

    def handle(self, *args, **kwargs):
        fast_mode = kwargs.pop("fast")
        date = kwargs.pop("date")

        if date:
            date = datetime.strptime(date, "%Y-%m-%d").date()
            transactions = Transaction.objects.order_by("timestamp", "pk").filter(timestamp__date__gte=date)
        elif fast_mode:
            first_tx_with_no_cost_basis = (
                Transaction.objects.filter(
                    Q(from_detail__isnull=False) & Q(from_detail__cost_basis__isnull=True)
                    | Q(to_detail__isnull=False) & Q(to_detail__cost_basis__isnull=True)
                )
                .order_by("timestamp", "pk")
                .first()
            )

            if first_tx_with_no_cost_basis is None:
                print("All transactions cost basis has been calculated, nothing to do.")
                return

            transactions = Transaction.objects.order_by("timestamp", "pk").filter(
                timestamp__gte=first_tx_with_no_cost_basis.timestamp
            )
        else:
            transactions = Transaction.objects.all().order_by("timestamp", "pk")

        self.calculate_cost_bases(transactions)
