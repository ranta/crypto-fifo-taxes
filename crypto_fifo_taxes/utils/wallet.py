from decimal import Decimal

from django.conf import settings

from crypto_fifo_taxes.models import Wallet


def get_wallet_balance_sum() -> dict[str, Decimal]:
    wallet_sum = {}

    for wallet in Wallet.objects.all():
        balance = wallet.get_current_balance()
        for symbol, quantity in balance.items():
            if symbol in settings.IGNORED_TOKENS:
                continue
            wallet_sum[symbol] = wallet_sum[symbol] + quantity if symbol in wallet_sum else quantity
    return wallet_sum
