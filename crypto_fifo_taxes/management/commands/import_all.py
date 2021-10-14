from datetime import datetime

from django.core.management import BaseCommand, call_command
from django.db.transaction import atomic

from crypto_fifo_taxes.models import Transaction


class Command(BaseCommand):
    @atomic
    def handle(self, *args, **kwargs):
        transactions_count = Transaction.objects.count()
        start_time = datetime.now()

        # Import transactions
        call_command("sync_binance")
        call_command("import_coinbase_json")
        call_command("import_binance_eth2_json")
        call_command("import_nicehash")
        call_command("import_json")

        # Calculate cost basis, gains, losses
        call_command("cost_basis")

        print(f"\nTotal new transactions created: {Transaction.objects.count() - transactions_count}")
        print(f"Total time elapsed: {datetime.now() - start_time}")
