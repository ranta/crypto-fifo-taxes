import csv
import logging
import os
from datetime import datetime
from decimal import Decimal

import pytz
from django.conf import settings
from django.core.management import BaseCommand
from django.db.transaction import atomic

from crypto_fifo_taxes.enums import TransactionLabel
from crypto_fifo_taxes.models import Transaction, Wallet
from crypto_fifo_taxes.utils.currency import get_or_create_currency
from crypto_fifo_taxes.utils.transaction_creator import TransactionCreator

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    wallet = Wallet.objects.get(name="Nicehash")
    btc = get_or_create_currency(symbol="BTC")

    def add_arguments(self, parser) -> None:
        parser.add_argument("--file", type=str)

    @staticmethod
    def nstrptime(stamp: str) -> datetime:
        """
        Convert Nicehash datetime string to python datetime

        >>>nstrptime('2020-12-27 00:00:00 GMT')
        datetime.datetime(2020, 12, 27, 0, 0, tzinfo=<UTC>)
        """
        return datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S GMT").replace(tzinfo=pytz.UTC)

    def import_income_row(self, data, row: dict[str, str]) -> None:
        pass

    def import_fee_row(self, data, row: dict[str, str]) -> None:
        pass

    def get_tx_td(self, date: str):
        return f"Nicehash-{self.nstrptime(date).date()}"

    def import_data(self, data: list[dict[str, str]]) -> None:
        dates = [r["Date time"] for r in data if r["Date time"] and r["Date time"] != "∑"]

        # Iterate by dates, because there are multiple transactions per date, and they should be combined
        for date in dates:
            tx_id = self.get_tx_td(date)

            # If data is already imported, skip date
            if Transaction.objects.filter(tx_id=tx_id).exists():
                continue

            # Get nicehash transactions with the same date
            nicehash_transactions = [r for r in data if r["Date time"] == date]
            assert len(nicehash_transactions) == 2  # Reward and Fee
            reward = next(filter(lambda r: r["Purpose"] == "Hashpower mining", nicehash_transactions))
            fee = next(filter(lambda r: r["Purpose"] == "Hashpower mining fee", nicehash_transactions))
            assert reward
            assert fee

            tx_creator = TransactionCreator(
                timestamp=self.nstrptime(date),
                tx_id=tx_id,
                description="Nicehash csv imported transaction",
                label=TransactionLabel.MINING,
                fill_cost_basis=False,
            )
            tx_creator.add_to_detail(wallet=self.wallet, currency=self.btc, quantity=Decimal(reward["Amount (BTC)"]))
            tx_creator.add_fee_detail(wallet=self.wallet, currency=self.btc, quantity=abs(Decimal(fee["Amount (BTC)"])))
            tx_creator.create_deposit()

    @atomic
    def handle(self, *args, **kwargs) -> None:
        transactions_count = Transaction.objects.count()

        filename = kwargs.pop("file") or "nicehash_report.csv"
        filepath = os.path.join(settings.BASE_DIR, filename)

        with open(filepath) as csv_file:
            reader = csv.DictReader(csv_file)
            self.import_data(list(reader))

        logger.info(f"New transactions created: {Transaction.objects.count() - transactions_count}")
