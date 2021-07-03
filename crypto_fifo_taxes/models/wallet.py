from decimal import Decimal
from typing import List

from django.conf import settings
from django.db import models
from django.db.models import DecimalField, ExpressionWrapper, F, OuterRef, Sum, Window
from django.db.models.functions import Coalesce
from django.utils.translation import gettext as _

from crypto_fifo_taxes.models import Currency, TransactionDetail
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

    def __str__(self):
        return f"{self.user.get_full_name()}'s Wallet ({self.name})"

    def __repr__(self):
        return f"<{self.__class__.__name__} ({self.pk}): User: {self.user.username} ({self.name}))>"

    def get_used_currency_ids(self):
        """Returns a list of currencies that have ever passed through this wallet"""
        return self.transaction_details.values_list("currency_id", flat=True).distinct()

    def get_current_balance(self):
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

    def get_consumable_currency_balances(self, currency: Currency) -> List[TransactionDetail]:
        """
        Returns a list of "deposits" to the wallet after excluding any deposits,
        which have already been withdrawn from older to newer.

        Neither Django nor PostgreSQL support filtering rows by the values of a window function.
        This is overcome by wrapping the query and putting the `WHERE` clause in the outer query.
        refs. https://code.djangoproject.com/ticket/28333
        Another other option would be to filter deposits in Python, but it's not as efficient as filtering in the db.
        """

        # Total amount of currency that has left the wallet
        total_spent = self.transaction_details.filter(from_detail__isnull=False, currency=currency).aggregate(
            total_spent=Sum("quantity")
        )["total_spent"] or Decimal(0)

        # All deposits of currency to the wallet, annotated with
        # the sum of all earlier deposits and balance left after reducing total_spent.
        deposits = (
            self.transaction_details.filter(to_detail__isnull=False, currency=currency)
            .annotate(
                accum_quantity=Window(Sum(F("quantity")), order_by=F("to_detail__timestamp").asc()),
                balance_left=ExpressionWrapper(F("accum_quantity") - total_spent, output_field=DecimalField()),
            )
            .order_by("to_detail__timestamp")
        )

        # Convert to SQL to allow filtering by `accum_quantity`.
        # refs. https://blog.oyam.dev/django-filter-by-window-function/
        sql, params = deposits.query.sql_with_params()
        deposits_filtered = TransactionDetail.objects.raw(
            "SELECT * FROM ({}) deposits_with_accumed_quantity WHERE accum_quantity > %s".format(sql),
            [*params, total_spent],
        )
        return list(deposits_filtered)
