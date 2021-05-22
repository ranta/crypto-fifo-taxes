from django.db import models
from enumfields import EnumField

from crypto_fifo_taxes.enums import TradeType
from crypto_fifo_taxes.models import TransactionDecimalField


class Trade(models.Model):
    """Contains `static` values for a trade"""

    wallet = models.ForeignKey(
        to="Wallet",
        on_delete=models.CASCADE,
        related_name="trades",
    )
    pair = models.ForeignKey(
        to="CurrencyPair",
        on_delete=models.PROTECT,
        related_name="trades",
    )
    price = TransactionDecimalField()
    quantity = TransactionDecimalField()
    total_price = TransactionDecimalField()
    timestamp = models.DateTimeField()
    description = models.TextField(
        blank=True,
        default="",
    )
    trade_type = EnumField(TradeType)


class TradeExtra(models.Model):
    """Contains calculated prices for the trade in FIAT"""

    trade = models.OneToOneField(
        Trade,
        on_delete=models.CASCADE,
        related_name="extra",
    )
    from_cost_basis = TransactionDecimalField()
    to_cost_basis = TransactionDecimalField()
    fee_cost = TransactionDecimalField()


class TradeFee(models.Model):
    """Most trades have a fee and the fee can be in any currency"""
    trade = models.OneToOneField(
        Trade,
        on_delete=models.CASCADE,
        related_name="fee",
    )
    quantity = TransactionDecimalField()
    currency = models.ForeignKey(
        to="Currency",
        on_delete=models.PROTECT,
        related_name="+",
    )

class TradeFeeExtra(models.Model):
    """Contains calculated prices for the fee in FIAT"""
    fee = models.OneToOneField(
        TradeFee,
        on_delete=models.CASCADE,
        related_name="extra",
    )
    from_cost_basis = TransactionDecimalField()
    to_cost_basis = TransactionDecimalField()
