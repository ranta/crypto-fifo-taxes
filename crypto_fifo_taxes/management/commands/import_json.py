import json
import os
from decimal import Decimal
from typing import Optional

from django.conf import settings
from django.core.management import BaseCommand
from django.db.transaction import atomic

from crypto_fifo_taxes.enums import TransactionLabel, TransactionType
from crypto_fifo_taxes.models import Transaction, Wallet
from crypto_fifo_taxes.utils.binance.binance_api import bstrptime, to_timestamp
from crypto_fifo_taxes.utils.currency import get_or_create_currency
from crypto_fifo_taxes.utils.transaction_creator import TransactionCreator


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--file", type=str)

    def get_wallets(self, row: dict) -> tuple[Optional[Wallet], Optional[Wallet], Optional[Wallet]]:
        if "wallet" in row:
            wallet = Wallet.objects.get(name=row["wallet"])
            return wallet, wallet, wallet

        return (
            Wallet.objects.get(name=row["from_wallet"]) if "from_wallet" in row else None,
            Wallet.objects.get(name=row["to_wallet"]) if "to_wallet" in row else None,
            Wallet.objects.get(name=row["fee_wallet"]) if "fee_wallet" in row else None,
        )

    def build_transaction_id(self, row: dict) -> str:
        if "tx_id" in row:
            # Use existing transaction id if it exists
            return row["tx_id"]
        wallet = row["wallet"] if "wallet" in row else row["to_wallet"] if "to_wallet" in row else row["from_wallet"]
        timestamp = to_timestamp(bstrptime(row["timestamp"])) if "timestamp" in row else "0" * 8
        return f"{wallet}_{timestamp}"

    def update_existing_transaction(self, row: dict, tx_id: str):
        # tx_id provided, add provided information to an existing transaction
        transaction = Transaction.objects.filter(tx_id=tx_id).first()

        if transaction is None:
            print(
                f"Trying to update a transaction that has a tx_id ({tx_id}) set "
                f"but matching transaction was not found!"
            )
            return

        transaction.description = "Manually updated transaction"
        wallets = self.get_wallets(row)
        if "from_symbol" in row:
            transaction.add_detail(
                "from_detail",
                wallet=wallets[0],
                currency=get_or_create_currency(row["from_symbol"]),
                quantity=Decimal(str(row["from_amount"])),
            )
        if "to_symbol" in row:
            transaction.add_detail(
                "to_detail",
                wallet=wallets[1],
                currency=get_or_create_currency(row["to_symbol"]),
                quantity=Decimal(str(row["to_amount"])),
            )
        if "fee_symbol" in row:
            transaction.add_detail(
                "fee_detail",
                wallet=wallets[2],
                currency=get_or_create_currency(row["fee_symbol"]),
                quantity=Decimal(str(row["fee_amount"])),
            )
        if "type" in row:
            transaction.transaction_type = TransactionType[row["type"]]
            transaction.save()
        if "label" in row:
            transaction.transaction_label = TransactionLabel[row["label"]]
            transaction.save()

    def handle_imported_rows(self, data: list) -> None:
        tx_ids = set(self.build_transaction_id(row) for row in data)
        existing_transactions = Transaction.objects.filter(tx_id__in=tx_ids).values_list("tx_id", flat=True)

        for row in data:
            tx_id = self.build_transaction_id(row)

            # Update already imported transactions
            if tx_id in existing_transactions:
                self.update_existing_transaction(row, tx_id)
                continue

            wallets = self.get_wallets(row)
            tx_creator = TransactionCreator(
                timestamp=bstrptime(row["timestamp"]),
                description="Manually imported transaction",
                tx_id=tx_id,
                type=TransactionType[row["type"]],
                fill_cost_basis=False,
            )
            if "label" in row:
                tx_creator.label = TransactionLabel[row["label"]]

            if "from_symbol" in row:
                tx_creator.add_from_detail(
                    wallet=wallets[0],
                    currency=get_or_create_currency(row["from_symbol"]),
                    quantity=Decimal(str(row["from_amount"])),
                )
            if "to_symbol" in row:
                tx_creator.add_to_detail(
                    wallet=wallets[1],
                    currency=get_or_create_currency(row["to_symbol"]),
                    quantity=Decimal(str(row["to_amount"])),
                )
            if "fee_symbol" in row:
                tx_creator.add_fee_detail(
                    wallet=wallets[2],
                    currency=get_or_create_currency(row["fee_symbol"]),
                    quantity=Decimal(str(row["fee_amount"])),
                )

            tx_creator.create_transaction()

    @atomic
    def handle(self, *args, **kwargs):
        transactions_count = Transaction.objects.count()

        filename = kwargs.pop("file") or "import.json"
        filepath = os.path.join(settings.BASE_DIR, filename)

        with open(filepath) as json_file:
            data = json.load(json_file)
            self.handle_imported_rows(data)

        print(f"New transactions created: {Transaction.objects.count() - transactions_count}")
