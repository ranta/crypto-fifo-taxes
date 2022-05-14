from django.core.management import BaseCommand, call_command

from crypto_fifo_taxes.utils.wrappers import print_time_elapsed_new_transactions


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("-d", "--date", type=str, help="Start from this date. Format: YYYY-MM-DD")
        parser.add_argument("-m", "--mode", type=int, help="Mode this sync will be run in. 0=fast, 1=full")

    @print_time_elapsed_new_transactions
    def import_all(self):
        # Import transactions
        call_command("sync_binance", date=self.date, mode=self.mode)
        call_command("import_coinbase_json")
        call_command("import_binance_eth2_json")
        call_command("import_nicehash")
        call_command("import_json")

        # Fetch market prices for currencies
        call_command("fetch_market_prices", date=self.date)

        # Calculate cost basis, gains, losses
        call_command("cost_basis", date=self.date)

        # Generate snapshots for every day
        call_command("snapshot", date=self.date)

    def handle(self, *args, **kwargs):
        self.date = kwargs.pop("date")
        self.mode = kwargs.pop("mode")

        self.import_all()
