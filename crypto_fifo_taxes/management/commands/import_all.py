from django.core.management import BaseCommand, call_command
from django.db.transaction import atomic


class Command(BaseCommand):
    @atomic
    def handle(self, *args, **kwargs):
        # Import transactions
        call_command("sync_binance")
        call_command("import_coinbase_json")
        call_command("import_binance_eth2_json")
        call_command("import_nicehash")
        call_command("import_json")

        # Calculate cost basis, gains, losses
        call_command("cost_basis")
