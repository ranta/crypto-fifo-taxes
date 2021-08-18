from decimal import Decimal

from crypto_fifo_taxes.models import Wallet
from crypto_fifo_taxes.utils.binance_api import bstrptime, from_timestamp
from crypto_fifo_taxes.utils.currency import get_or_create_currency
from crypto_fifo_taxes.utils.transaction_creator import TransactionCreator


def import_deposits(wallet: Wallet, deposits: list) -> None:
    """
    https://binance-docs.github.io/apidocs/spot/en/#deposit-history-supporting-network-user_data
    """
    for deposit in deposits:
        currency = get_or_create_currency(deposit["coin"])
        TransactionCreator().create_deposit(
            wallet=wallet,
            timestamp=from_timestamp(deposit["insertTime"]),
            currency=currency,
            quantity=Decimal(deposit["amount"]),
        )


def import_withdrawals(wallet: Wallet, deposits: list) -> None:
    """
    https://binance-docs.github.io/apidocs/spot/en/#withdraw-history-supporting-network-user_data
    """
    for withdrawal in deposits:
        if withdrawal["transferType"] == 1:  # Internal transfer
            continue

        currency = get_or_create_currency(withdrawal["coin"])
        tx_creator = TransactionCreator()
        tx_creator.add_fee_detail(wallet=wallet, currency=currency, quantity=Decimal(withdrawal["transactionFee"]))
        tx_creator.create_withdrawal(
            timestamp=bstrptime(withdrawal["applyTime"]),
            wallet=wallet,
            currency=currency,
            quantity=Decimal(withdrawal["amount"]),
        )
