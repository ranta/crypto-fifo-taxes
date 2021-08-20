from decimal import Decimal

from crypto_fifo_taxes.models import Wallet
from crypto_fifo_taxes.utils.binance_api import bstrptime, from_timestamp
from crypto_fifo_taxes.utils.currency import get_or_create_currency
from crypto_fifo_taxes.utils.transaction_creator import TransactionCreator


def import_deposits(wallet: Wallet, deposits: list) -> None:
    """
    https://binance-docs.github.io/apidocs/spot/en/#deposit-history-supporting-network-user_data
    """
    importable_txs = set(t["txId"] for t in deposits)
    existing_transactions = Transaction.objects.filter(tx_id__in=importable_txs).values_list("tx_id", flat=True)

    for deposit in deposits:
        # If transaction has already been imported, skip it
        if deposit["txId"] in existing_transactions:
            continue

        currency = get_or_create_currency(deposit["coin"])
        TransactionCreator(fill_cost_basis=False).create_deposit(
            wallet=wallet,
            timestamp=from_timestamp(deposit["insertTime"]),
            currency=currency,
            quantity=Decimal(deposit["amount"]),
            tx_id=deposit["txId"],
        )


def import_withdrawals(wallet: Wallet, deposits: list) -> None:
    """
    https://binance-docs.github.io/apidocs/spot/en/#withdraw-history-supporting-network-user_data
    """
    importable_txs = set(t["txId"] for t in deposits)
    existing_transactions = Transaction.objects.filter(tx_id__in=importable_txs).values_list("tx_id", flat=True)

    for withdrawal in deposits:
        if withdrawal["transferType"] == 1:  # Internal transfer
            continue

        # If transaction has already been imported, skip it
        if withdrawal["txId"] in existing_transactions:
            continue

        currency = get_or_create_currency(withdrawal["coin"])
        tx_creator = TransactionCreator(fill_cost_basis=False)
        tx_creator.add_fee_detail(wallet=wallet, currency=currency, quantity=Decimal(withdrawal["transactionFee"]))
        tx_creator.create_withdrawal(
            timestamp=bstrptime(withdrawal["applyTime"]),
            wallet=wallet,
            currency=currency,
            quantity=Decimal(withdrawal["amount"]),
            tx_id=withdrawal["txId"],
        )
