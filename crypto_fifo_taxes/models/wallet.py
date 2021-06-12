from django.conf import settings
from django.db import models
from django.utils.translation import gettext as _

from crypto_fifo_taxes.models import Currency


class Wallet(models.Model):
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wallets",
    )
    name = models.CharField(
        max_length=50,
        verbose_name=_("Wallet Name"),
    )
    icon = models.ImageField(
        upload_to="wallet_icons",
        verbose_name=_("Icon"),
        blank=True,
        null=True,
    )
    fiat = models.ForeignKey(
        to=Currency,
        on_delete=models.CASCADE,
        related_name="wallets",
        verbose_name=_("FIAT"),
    )

    def get_currencies(self):
        """Return all currencies used in this wallet"""
        pass
