from django.db import models

from crypto_fifo_taxes.utils.models import TransactionDecimalField


class WalletTransfer(models.Model):
    from_wallet = models.ForeignKey(
        to="Wallet",
        on_delete=models.CASCADE,
        related_name="sent_transfers",
    )
    to_wallet = models.ForeignKey(
        to="Wallet",
        on_delete=models.CASCADE,
        related_name="received_transfers",
    )
    from_currency = models.ForeignKey(
        to="Currency",
        on_delete=models.PROTECT,
        related_name="sent_transfers",
    )
    to_currency = models.ForeignKey(
        to="Currency",
        on_delete=models.PROTECT,
        related_name="received_transfers",
    )
    from_amount = TransactionDecimalField()
    to_amount = TransactionDecimalField()
