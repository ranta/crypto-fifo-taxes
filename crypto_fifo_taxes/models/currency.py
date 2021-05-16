from django.db import models
from django.utils.translation import gettext as _

from crypto_fifo_taxes.models import TransactionDecimalField


class Currency(models.Model):
    # eg. "BTC"
    symbol = models.CharField(
        max_length=30,
        verbose_name=_("Symbol"),
        unique=True,
    )
    name = models.CharField(
        max_length=30,
        verbose_name=_("Name"),
        unique=True,
    )
    icon = models.ImageField(
        upload_to="coin_icons",
        verbose_name=_("Icon"),
    )
    fiat = models.BooleanField(default=False)


class CurrencyPair(models.Model):
    # eg. "BTCUSDT"
    symbol = models.CharField(max_length=30)
    buy = models.ForeignKey(
        to=Currency,
        on_delete=models.PROTECT,
        related_name="buy_pairs",
    )
    sell = models.ForeignKey(
        to=Currency,
        on_delete=models.PROTECT,
        related_name="sell_pairs",
    )


class CurrencyPrice(models.Model):
    """Crypto price in FIAT on a specific date"""

    currency = models.ForeignKey(
        to=Currency,
        on_delete=models.PROTECT,
        related_name="prices",
    )
    date = models.DateField()
    value = TransactionDecimalField()

    # TODO make Currency and Date unique together constraint
