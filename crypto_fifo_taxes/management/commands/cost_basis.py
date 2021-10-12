from django.core.management import BaseCommand
from django.db.transaction import atomic

from crypto_fifo_taxes.models import Transaction


class Command(BaseCommand):
    @atomic
    def handle(self, *args, **options):
        transactions = Transaction.objects.all().order_by("timestamp", "pk")
        count = transactions.count()
        for i, t in enumerate(transactions):
            print(f"Calculating cost basis for transactions. {i / count * 100:>5.2f}% ({t.timestamp.date()})", end="\r")
            t.fill_cost_basis()
