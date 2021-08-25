from decimal import Decimal

from django.conf import settings

from crypto_fifo_taxes.models import CurrencyPair, Transaction, Wallet
from crypto_fifo_taxes.utils.binance.binance_api import bstrptime, from_timestamp
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


def import_pair_trades(wallet: Wallet, trading_pair: CurrencyPair, trades: list) -> None:
    """
    https://binance-docs.github.io/apidocs/spot/en/#account-trade-list-user_data
    """
    assert wallet is not None
    assert trading_pair is not None

    importable_orders = set(str(t["orderId"]) for t in trades)
    existing_orders = Transaction.objects.filter(tx_id__in=importable_orders).values_list("tx_id", flat=True)

    for trade in trades:
        # If order has already been imported, skip it
        if str(trade["orderId"]) in existing_orders:
            continue

        fee_currency = get_or_create_currency(trade["commissionAsset"])

        tx_creator = TransactionCreator(fill_cost_basis=False)
        if trade["isBuyer"]:
            tx_creator.add_from_detail(wallet=wallet, currency=trading_pair.sell, quantity=Decimal(trade["quoteQty"]))
            tx_creator.add_to_detail(wallet=wallet, currency=trading_pair.buy, quantity=Decimal(trade["qty"]))
        else:
            tx_creator.add_from_detail(wallet=wallet, currency=trading_pair.buy, quantity=Decimal(trade["qty"]))
            tx_creator.add_to_detail(wallet=wallet, currency=trading_pair.sell, quantity=Decimal(trade["quoteQty"]))
        tx_creator.add_fee_detail(wallet=wallet, currency=fee_currency, quantity=Decimal(trade["commission"]))
        tx_creator.create_trade(timestamp=from_timestamp(trade["time"]), tx_id=str(trade["orderId"]))


def import_dust(wallet: Wallet, converts: list) -> None:
    """
    https://binance-docs.github.io/apidocs/spot/en/#dustlog-user_data
    """
    convert_ids = set(str(t["transId"]) for t in converts)
    existing_converts = Transaction.objects.filter(tx_id__in=convert_ids).values_list("tx_id", flat=True)

    bnb = get_or_create_currency("BNB")

    for convert in converts:
        # If order has already been imported, skip it
        if str(convert["transId"]) in existing_converts:
            continue

        for detail in convert["userAssetDribbletDetails"]:
            from_currency = get_or_create_currency(detail["fromAsset"])

            tx_creator = TransactionCreator(fill_cost_basis=False)
            tx_creator.add_from_detail(wallet=wallet, currency=from_currency, quantity=Decimal(detail["amount"]))
            tx_creator.add_to_detail(wallet=wallet, currency=bnb, quantity=Decimal(detail["transferedAmount"]))
            tx_creator.add_fee_detail(wallet=wallet, currency=bnb, quantity=Decimal(detail["serviceChargeAmount"]))
            tx_creator.create_trade(timestamp=from_timestamp(convert["operateTime"]), tx_id=str(convert["transId"]))


def import_dividends(wallet: Wallet, dividends: list) -> None:
    """
    https://binance-docs.github.io/apidocs/spot/en/#asset-dividend-record-user_data
    """
    dividend_ids = set(str(t["tranId"]) for t in dividends)
    existing_dividends = Transaction.objects.filter(tx_id__in=dividend_ids).values_list("tx_id", flat=True)

    for dividend in dividends:
        if str(dividend["tranId"]) in existing_dividends:
            continue

        if dividend["asset"] in settings.IGNORED_TOKENS:
            continue

        currency = get_or_create_currency(dividend["asset"])
        tx_creator = TransactionCreator(
            timestamp=from_timestamp(dividend["divTime"]),
            fill_cost_basis=False,
            tx_id=dividend["tranId"],
            description=dividend["enInfo"],
        )
        tx_creator.add_to_detail(wallet=wallet, currency=currency, quantity=Decimal(dividend["amount"]))

        if dividend["enInfo"] == "VEN/VET Mainnet Swap(1:100) ":
            # VEN/VET Swap is included in dividends, so VET is added to wallet, but VEN is not removed.
            tx_creator.add_from_detail(
                wallet=wallet, currency=get_or_create_currency("VEN"), quantity=Decimal(dividend["amount"]) / 100
            )
            tx_creator.create_swap()
            continue

        tx_creator.create_deposit()
