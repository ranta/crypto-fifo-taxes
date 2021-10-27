import time
from datetime import datetime
from typing import Union

from binance.exceptions import BinanceAPIException
from django.core.management import BaseCommand
from django.db.transaction import atomic

from crypto_fifo_taxes.models import CurrencyPair, Transaction, Wallet
from crypto_fifo_taxes.utils.binance.binance_api import (
    get_binance_client,
    get_binance_deposits,
    get_binance_dividends,
    get_binance_dust_log,
    get_binance_interest_history,
    get_binance_withdraws,
)
from crypto_fifo_taxes.utils.binance.binance_importer import (
    import_deposits,
    import_dividends,
    import_dust,
    import_interest,
    import_pair_trades,
    import_withdrawals,
)
from crypto_fifo_taxes.utils.currency import get_or_create_currency_pair
from crypto_fifo_taxes.utils.wrappers import print_time_elapsed


class Command(BaseCommand):
    client = get_binance_client()
    wallet = Wallet.objects.get(name="Binance")
    mode = 0  # Fast mode

    def add_arguments(self, parser):
        # Optional argument
        parser.add_argument(
            "-m",
            "--mode",
            type=int,
            help="Mode this sync will be run in. 0=fast, 1=full",
        )

    def print_dot(self):
        print(".", end="", flush=True)

    def get_all_pairs(self) -> list:
        """
        Get a list of all trading pairs in Binance

        Format:
        {'symbol': 'ETHBTC', 'baseAsset': 'ETH', 'quoteAsset': 'BTC'}
        """
        exchange_info = self.client.get_exchange_info()
        all_pairs = [
            {"symbol": s["symbol"], "baseAsset": s["baseAsset"], "quoteAsset": s["quoteAsset"]}
            for s in exchange_info["symbols"]
        ]
        return all_pairs

    def sync_pair(self, pair: Union[dict, str]):
        while True:
            try:
                # Full sync
                if type(pair) == dict:
                    trades = self.client.get_my_trades(symbol=pair["symbol"])
                    trading_pair = None
                    if trades != []:
                        trading_pair = get_or_create_currency_pair(
                            symbol=pair["symbol"],
                            buy=pair["baseAsset"],
                            sell=pair["quoteAsset"],
                        )
                    time.sleep(0.1)  # Reduce the frequency of cooldowns
                # Fast sync
                else:
                    trades = self.client.get_my_trades(symbol=pair)
                    trading_pair = CurrencyPair.objects.get(symbol=pair)

                if trading_pair is not None:
                    print(trading_pair, end=".", flush=True)
                    import_pair_trades(wallet=self.wallet, trading_pair=trading_pair, trades=trades)
                else:
                    self.print_dot()
                break
            except BinanceAPIException as e:
                if "Too much request weight used" in str(e):
                    print("\nToo much Binance API weight used, on cooldown", end="")
                    time.sleep(15)  # API cool down time is not accessible. Try again soon

    @print_time_elapsed
    def sync_deposits(self) -> None:
        for deposits in get_binance_deposits():
            self.print_dot()
            import_deposits(self.wallet, deposits)

    @print_time_elapsed
    def sync_withdrawals(self) -> None:
        for withdraws in get_binance_withdraws():
            self.print_dot()
            import_withdrawals(self.wallet, withdraws)

    @print_time_elapsed
    def sync_dust(self):
        import_dust(self.wallet, get_binance_dust_log())

    @print_time_elapsed
    def sync_dividends(self):
        for dividends in get_binance_dividends():
            self.print_dot()
            import_dividends(self.wallet, dividends)

    @print_time_elapsed
    def sync_interest(self):
        for dividends in get_binance_interest_history():
            self.print_dot()
            import_interest(self.wallet, dividends)

    @print_time_elapsed
    def sync_trades(self) -> None:
        pairs = []
        if not self.mode:
            # FAST sync
            # Sync only trading pairs which already have records
            pairs = CurrencyPair.objects.values_list("symbol", flat=True)
            if len(pairs) > 1:
                print(f"Syncing trades using FAST mode for {len(pairs)} pairs...", end="")
            else:
                print("No existing currency pairs found for FAST mode sync. Running in FULL sync.")
                self.mode = 1

        if self.mode == 1:
            # FULL sync
            # Fetch any new trading pairs from Binance
            pairs = self.get_all_pairs()
            print(f"Syncing trades using FULL mode for {len(pairs)} pairs. This will take over ten minutes...")

        print("Syncing trades for pair: ", end="")
        for pair in pairs:
            self.sync_pair(pair)

    @atomic
    def handle(self, *args, **kwargs):
        sync_start_time = datetime.now()
        transactions_count = Transaction.objects.count()

        self.mode = kwargs.pop("mode")

        self.sync_trades()
        self.sync_deposits()
        self.sync_withdrawals()
        self.sync_dust()
        self.sync_dividends()
        self.sync_interest()

        print(f"Total time elapsed: {datetime.now() - sync_start_time}")
        print(f"New transactions created: {Transaction.objects.count() - transactions_count}")
