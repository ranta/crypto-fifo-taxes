import json
import os
from decimal import Decimal

from django.conf import settings
from django.core.management import BaseCommand
from django.db.transaction import atomic

from crypto_fifo_taxes.enums import TransactionType
from crypto_fifo_taxes.models import Wallet
from crypto_fifo_taxes.utils.binance.binance_api import bstrptime
from crypto_fifo_taxes.utils.currency import get_or_create_currency
from crypto_fifo_taxes.utils.transaction_creator import TransactionCreator


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--file", type=str)

    def get_wallets(self, row: dict) -> tuple[Wallet, Wallet]:
        if "from_wallet" in row and "to_wallet" in row:
            return Wallet.objects.get(name=row["from_wallet"]), Wallet.objects.get(name=row["to_wallet"])
        wallet = Wallet.objects.get(name=row["wallet"])
        return wallet, wallet

    def handle_imported_rows(self, data):
        for row in data:
            wallets = self.get_wallets(row)
            tx_creator = TransactionCreator(
                fill_cost_basis=False,
                timestamp=bstrptime(row["timestamp"]),
                type=TransactionType[row["type"]],
            )

            if "from_symbol" in row:
                tx_creator.add_from_detail(
                    wallet=wallets[0],
                    currency=get_or_create_currency(row["from_symbol"]),
                    quantity=Decimal(row["from_amount"]),
                )
            if "to_symbol" in row:
                tx_creator.add_to_detail(
                    wallet=wallets[1],
                    currency=get_or_create_currency(row["to_symbol"]),
                    quantity=Decimal(row["to_amount"]),
                )

            tx_creator.create_transaction()

    @atomic
    def handle(self, *args, **kwargs):
        filename = kwargs.pop("file", "import.json")
        filepath = os.path.join(settings.BASE_DIR, "app", filename)

        with open(filepath) as json_file:
            data = json.load(json_file)
            self.handle_imported_rows(data)
