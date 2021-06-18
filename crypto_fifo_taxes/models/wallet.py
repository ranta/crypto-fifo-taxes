from django.conf import settings
from django.db import models
from django.db.models import DecimalField, ExpressionWrapper, F, OuterRef
from django.db.models.functions import Coalesce
from django.utils.translation import gettext as _

from crypto_fifo_taxes.models import Currency
from crypto_fifo_taxes.utils.db import SQSum


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

    def get_used_currency_ids(self):
        """Returns a list of currencies that have ever passed through this wallet"""
        return self.transaction_details.values_list("currency_id", flat=True).distinct()

    def get_balance(self):
        """Returns wallet's current currencies balances"""
        return (
            self.transaction_details.annotate(
                symbol=F("currency__symbol"),
                deposits=SQSum(
                    self.transaction_details.filter(
                        currency_id=OuterRef("currency_id"),
                        to_detail__isnull=False,
                    ),
                    sum_field="quantity",
                ),
                withdrawals=SQSum(
                    self.transaction_details.filter(
                        currency_id=OuterRef("currency_id"),
                        from_detail__isnull=False,
                    ),
                    sum_field="quantity",
                ),
                balance=ExpressionWrapper(
                    Coalesce(F("deposits"), 0) - Coalesce(F("withdrawals"), 0), output_field=DecimalField()
                ),
            )
            .order_by("currency_id")
            .distinct("currency_id")
        )
