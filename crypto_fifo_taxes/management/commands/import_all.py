from django.core.management import BaseCommand, call_command

from crypto_fifo_taxes.utils.wrappers import print_time_elapsed_new_transactions


class Command(BaseCommand):

    @print_time_elapsed_new_transactions
    def import_all(self):
        # Import transactions
        call_command("sync_binance")
        call_command("import_coinbase_json")
        call_command("import_binance_eth2_json")
        call_command("import_nicehash")
        call_command("import_json")

        # Calculate cost basis, gains, losses
        call_command("cost_basis")

    def handle(self, *args, **kwargs):

        self.import_all()
