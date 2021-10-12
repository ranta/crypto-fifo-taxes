from django.core.management import BaseCommand
from django.db.transaction import atomic

from crypto_fifo_taxes.models import Transaction


class Command(BaseCommand):
    @atomic
    def handle(self, *args, **options):
        transactions = Transaction.objects.all().order_by("timestamp", "pk")

        for t in transactions:
            t.fill_cost_basis()
