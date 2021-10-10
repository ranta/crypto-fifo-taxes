import json
import os
from decimal import Decimal

from django.conf import settings
from django.core.management import BaseCommand
from django.db.transaction import atomic

from crypto_fifo_taxes.enums import TransactionLabel, TransactionType
from crypto_fifo_taxes.models import Transaction, Wallet
from crypto_fifo_taxes.utils.binance.binance_api import from_timestamp, to_timestamp
from crypto_fifo_taxes.utils.currency import get_or_create_currency
from crypto_fifo_taxes.utils.transaction_creator import TransactionCreator


class Command(BaseCommand):
    wallet = Wallet.objects.get(name="Binance")

    def add_arguments(self, parser):
        parser.add_argument("--file", type=str)

    def build_transaction_id(self, row: dict) -> str:
        timestamp = to_timestamp(from_timestamp(int(row["day"])).replace(hour=0, minute=0, second=0))
        return f"{self.wallet.name}_{timestamp}_{row['amount']}_{row['positionToken']}"

    def handle_imported_rows(self, data: list) -> None:
        tx_ids = set(self.build_transaction_id(row) for row in data)
        existing_transactions = Transaction.objects.filter(tx_id__in=tx_ids).values_list("tx_id", flat=True)

        for row in data:
            tx_id = self.build_transaction_id(row)
            if tx_id in existing_transactions:
                continue

            tx_creator = TransactionCreator(
                timestamp=from_timestamp(int(row["day"])),
                tx_id=tx_id,
                description="Manually Imported ETH 2.0 Staking Transaction",
                type=TransactionType.DEPOSIT,
                label=TransactionLabel.REWARD,
                fill_cost_basis=False,
            )
            tx_creator.add_to_detail(
                wallet=self.wallet,
                currency=get_or_create_currency(row["positionToken"]),
                quantity=Decimal(row["amount"]),
            )
            tx_creator.create_transaction()

    @atomic
    def handle(self, *args, **kwargs):
        transactions_count = Transaction.objects.count()

        filename = kwargs.pop("file") or "binance_eth2_staking.json"
        filepath = os.path.join(settings.BASE_DIR, filename)

        with open(filepath) as json_file:
            data = json.load(json_file)
            self.handle_imported_rows(data)

        print(f"New transactions created: {Transaction.objects.count() - transactions_count}")
