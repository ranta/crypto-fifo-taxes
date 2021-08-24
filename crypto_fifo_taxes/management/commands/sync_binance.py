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
    get_binance_withdraws,
)
from crypto_fifo_taxes.utils.binance.binance_importer import (
    import_deposits,
    import_dividends,
    import_dust,
    import_pair_trades,
    import_withdrawals,
)
from crypto_fifo_taxes.utils.currency import get_or_create_currency_pair


class Command(BaseCommand):
    client = get_binance_client()
    wallet = Wallet.objects.get(name="Binance")

    def add_arguments(self, parser):
        # Optional argument
        parser.add_argument(
            "-m",
            "--mode",
            type=int,
            help="Mode this sync will be run in. 0=fast, 1=full",
        )

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
                # Fast sync
                else:
                    trades = self.client.get_my_trades(symbol=pair)
                    trading_pair = CurrencyPair.objects.get(symbol=pair)

                if trading_pair is not None:
                    print(f"\nSyncing trades for pair: {trading_pair}", end="")
                    import_pair_trades(wallet=self.wallet, trading_pair=trading_pair, trades=trades)
                else:
                    print(".", end="")
                break
            except BinanceAPIException as e:
                if "Too much request weight used" in str(e):
                    print("\nToo much Binance API weight used, on cooldown", end="")
                    time.sleep(20)  # API cool down time is not accessible. Try again in 20s

    def sync_deposits(self) -> None:
        for deposits in get_binance_deposits():
            print(".", end="")
            import_deposits(self.wallet, deposits)

    def sync_withdrawals(self) -> None:
        for withdraws in get_binance_withdraws():
            print(".", end="")
            import_withdrawals(self.wallet, withdraws)

    def sync_dust(self):
        import_dust(self.wallet, get_binance_dust_log())

    def sync_dividends(self):
        for dividends in get_binance_dividends():
            print(".", end="")
            import_dividends(self.wallet, dividends)

    def sync_trades(self, mode: int) -> None:
        if mode is None or mode == 0:
            # FAST sync
            # Sync only trading pairs which already have records
            pairs = CurrencyPair.objects.values_list("symbol", flat=True)
            if len(pairs) > 1:
                print(f"Syncing trades using FAST mode for {len(pairs)} pairs...")
            else:
                print("No existing currency pairs found for FAST mode sync. Manually run FULL sync.")
        else:
            # FULL sync
            # Fetch any new trading pairs from Binance
            pairs = self.get_all_pairs()
            print(f"Syncing trades using FULL mode for {len(pairs)} pairs...")

        for pair in pairs:
            self.sync_pair(pair)
        print()

    def print_time_elapsed(self, func, **kwargs):
        print(f"Starting {func.__name__}.", end="")
        part_start_time = datetime.now()
        func(**kwargs)
        print(f" Complete! Time elapsed: {datetime.now() - part_start_time}")

    @atomic
    def handle(self, *args, **kwargs):
        sync_start_time = datetime.now()
        transactions_count = Transaction.objects.count()

        mode = kwargs.pop("mode")
        self.print_time_elapsed(self.sync_trades, mode=mode)
        self.print_time_elapsed(self.sync_deposits)
        self.print_time_elapsed(self.sync_withdrawals)
        self.print_time_elapsed(self.sync_dust)
        self.print_time_elapsed(self.sync_dividends)

        print(f"Total time elapsed: {datetime.now() - sync_start_time}")
        print(f"New transactions created: {Transaction.objects.count() - transactions_count}")
