from decimal import Decimal

from django.conf import settings

from crypto_fifo_taxes.models import Wallet
from crypto_fifo_taxes.utils.binance.binance_api import get_binance_client


def get_binance_wallet_balance() -> dict[str:Decimal]:
    client = get_binance_client()
    balances: dict[str, Decimal] = {}

    # SPOT Wallet
    for row in client.get_account()["balances"]:
        symbol = row["asset"]
        if not Decimal(row["free"]) and not Decimal(row["locked"]):
            continue
        if symbol in settings.IGNORED_TOKENS:
            continue
        # Lending asset, ignore here as they are imported more accurately from the EARN endpoints
        if len(symbol) >= 5 and symbol.startswith("LD"):
            continue
        balances[symbol] = Decimal(row["free"]) + Decimal(row["locked"])

    # EARN Wallet (Flexible)
    for row in client.get_earn_flexible_position(size=100)["rows"]:
        symbol = row["asset"]
        if symbol in balances:
            balances[symbol] += Decimal(row["totalAmount"])
        else:
            balances[symbol] = Decimal(row["totalAmount"])

    # EARN Wallet (Locked)
    for row in client.get_earn_locked_position(size=100)["rows"]:
        symbol = row["asset"]
        if symbol in balances:
            balances[symbol] += Decimal(row["amount"])
        else:
            balances[symbol] = Decimal(row["amount"])

    return balances


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
