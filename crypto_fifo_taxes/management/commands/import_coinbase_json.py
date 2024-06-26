import json
import logging
import os
import sys
from datetime import UTC, datetime
from decimal import Decimal

from django.conf import settings
from django.core.management import BaseCommand
from django.db.transaction import atomic

from crypto_fifo_taxes.models import Transaction, Wallet
from crypto_fifo_taxes.utils.currency import get_or_create_currency, get_or_create_currency_pair
from crypto_fifo_taxes.utils.transaction_creator import TransactionCreator

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    wallet = Wallet.objects.get(name="Coinbase")

    def add_arguments(self, parser):
        parser.add_argument("--file", type=str)

    def handle_imported_rows(self, data):
        trade_ids = {str(row["trade id"]) for row in data}
        existing_orders = Transaction.objects.filter(tx_id__in=trade_ids).values_list("tx_id", flat=True)

        for row in data:
            # Skip already imported trades
            if str(row["trade id"]) in existing_orders:
                continue

            tx_creator = TransactionCreator(
                timestamp=datetime.strptime(row["created at"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=UTC),
                description="Manually imported Coinbase transaction",
                tx_id=row["trade id"],
                fill_cost_basis=False,
            )

            pair = get_or_create_currency_pair(
                symbol=row["product"].replace("-", ""),
                buy=row["product"].split("-")[0],
                sell=row["product"].split("-")[1],
            )

            size = Decimal(str(row["size"]))
            if row["side"] == "BUY":
                tx_creator.add_from_detail(
                    wallet=self.wallet, currency=pair.sell, quantity=Decimal(str(row["price"])) * size
                )
                tx_creator.add_to_detail(wallet=self.wallet, currency=pair.buy, quantity=size)
            else:
                tx_creator.add_from_detail(wallet=self.wallet, currency=pair.buy, quantity=size)
                tx_creator.add_to_detail(
                    wallet=self.wallet, currency=pair.sell, quantity=Decimal(str(row["price"])) * size
                )

            if row["fee"] > 0:
                tx_creator.add_fee_detail(
                    wallet=self.wallet,
                    currency=get_or_create_currency(row["price/fee/total unit"]),
                    quantity=Decimal(str(row["fee"])),
                )

            tx_creator.create_trade()

    @atomic
    def handle(self, *args, **kwargs):
        transactions_count = Transaction.objects.count()

        filename = kwargs.pop("file") or "coinbase_fills.json"
        filepath = os.path.join(settings.BASE_DIR, filename)

        with open(filepath) as json_file:
            data = json.load(json_file)
            self.handle_imported_rows(data)

        logger.info(f"New transactions created: {Transaction.objects.count() - transactions_count}")
