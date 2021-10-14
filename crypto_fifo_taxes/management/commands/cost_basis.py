from django.core.management import BaseCommand
from django.db.models import Q

from crypto_fifo_taxes.models import Transaction


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--fast", type=int)

    def handle(self, *args, **kwargs):
        self.fast_mode = kwargs.pop("fast", 0)

        if self.fast_mode:
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

        count = transactions.count()
        for i, t in enumerate(transactions):
            print(f"Calculating cost basis for transactions. {i / count * 100:>5.2f}% ({t.timestamp.date()})", end="\r")
            t.fill_cost_basis()
