from decimal import Decimal

from django.conf import settings

from crypto_fifo_taxes.models import Wallet
from crypto_fifo_taxes.utils.binance.binance_api import get_binance_client


def get_binance_wallet_balance() -> dict[str:Decimal]:
    def filter_spot_balances(row):
        if row["asset"] in settings.IGNORED_TOKENS:
            return False
        if len(row["asset"]) >= 5 and row["asset"].startswith("LD"):
            # Lending asset
            return False
        return Decimal(row["free"]) > 0 or Decimal(row["locked"]) > 0

    def filter_savings_balances(row):
        return Decimal(row["totalAmount"]) > 0

    client = get_binance_client()

    # Get positive balances from binance SPOT and SAVINGS accounts
    spot_wallet = filter(filter_spot_balances, client.get_account()["balances"])
    savings_wallet = filter(filter_savings_balances, client.get_lending_position())

    # Combine balances
    balances = {}
    for row in spot_wallet:
        balances[row["asset"]] = Decimal(row["free"]) + Decimal(row["locked"])
    for row in savings_wallet:
        if row["asset"] in balances.keys():
            balances[row["asset"]] = balances[row["asset"]] + Decimal(row["totalAmount"])
        else:
            balances[row["asset"]] = Decimal(row["totalAmount"])
    for symbol, quantity in settings.LOCKED_STAKING.items():
        if symbol in balances.keys():
            balances[symbol] = balances[symbol] + quantity
        else:
            balances[symbol] = quantity

    # Remove zero balances
    balance_diff = {}
    for symbol, quantity in balances.items():
        if quantity != Decimal(0):
            balance_diff[symbol] = quantity

    return balance_diff


def get_binance_wallet_differences() -> dict[str, Decimal]:
    """
    Return the balance differences of tokens of:
    `Binance live wallet balance` - `local calculated wallet balance`

    Positive balance = Deposit transactions are missing, local wallet is missing funds that are in Binance Wallet
    Negative balance = Too much withdrawal transactions, again most likely deposits are missing 😅
    """
    live_wallet = get_binance_wallet_balance()
    local_wallet = Wallet.objects.get(name="Binance").get_current_balance()

    for symbol, quantity in local_wallet.items():
        if symbol in live_wallet:
            live_wallet[symbol] = live_wallet[symbol] - quantity
        else:
            live_wallet[symbol] = -quantity

    # Remove zero balances
    balance_diff = {}
    for symbol, quantity in live_wallet.items():
        if quantity != Decimal(0):
            balance_diff[symbol] = quantity

    return balance_diff
