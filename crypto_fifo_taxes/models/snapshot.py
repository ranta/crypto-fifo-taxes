import logging
from datetime import datetime, time
from decimal import Decimal
from typing import Any

import pytz
from django.conf import settings
from django.db import models
from django.db.models import F, Q, Sum

from crypto_fifo_taxes.exceptions import MissingPriceHistoryError
from crypto_fifo_taxes.utils.currency import get_currency
from crypto_fifo_taxes.utils.db import CoalesceZero
from crypto_fifo_taxes.utils.models import TransactionDecimalField

logger = logging.getLogger(__name__)


class Snapshot(models.Model):
    """Aggregate model for a snapshot of a user's balance at the end of a date"""

    user = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="snapshots")
    date = models.DateField()
    worth = TransactionDecimalField(null=True, blank=True)
    cost_basis = TransactionDecimalField(null=True, blank=True)
    deposits = TransactionDecimalField(null=True, blank=True)

    class Meta:
        ordering = ("date",)

    def __str__(self):
        return f"{self.user.get_full_name()}'s Snapshot for {self.date}"

    def __repr__(self):
        return f"<{self.__class__.__name__} ({self.pk}): User: {self.user.username} ({self.date}))>"

    def get_balances(self, include_zero_balances: bool = False) -> list[dict[str, Any]]:
        """Return the last calculated snapshot balance for user"""
        values_qs = (
            SnapshotBalance.objects.filter(snapshot__date__lte=self.date)
            .order_by("currency_id", "-snapshot__date")
            .distinct("currency_id")
            .values("currency_id", "currency__symbol", "quantity", "cost_basis")
        )
        if not include_zero_balances:
            return [c for c in values_qs if c["quantity"] != 0]
        return values_qs

    def calculate_worth(self):
        from crypto_fifo_taxes.enums import TransactionLabel, TransactionType
        from crypto_fifo_taxes.models import TransactionDetail

        sum_worth = Decimal(0)
        sum_cost_basis = Decimal(0)

        balances = self.get_balances()
        for balance in balances:
            if balance["quantity"] == 0:
                continue

            currency = get_currency(balance["currency_id"])
            # For FIAT currencies we can simply add then, as their worth is their quantity
            if currency.is_fiat:
                sum_worth += balance["quantity"]
                sum_cost_basis += balance["cost_basis"]
                continue

            # For non-FIAT currencies we need to fetch their price
            try:
                currency_price = currency.get_fiat_price(date=self.date)
            # If the price is missing, we skip the currency and add its cost basis to the sums
            except MissingPriceHistoryError:
                logger.exception(f"Missing price for currency {currency}")

                sum_worth += balance["cost_basis"]
                sum_cost_basis += balance["cost_basis"]
                continue

            if currency_price is None:
                continue

            sum_worth += balance["quantity"] * currency_price.price
            sum_cost_basis += balance["quantity"] * balance["cost_basis"]

        # This defines what transactions are deposits
        deposits_filter = Q(
            Q(tx_timestamp__lte=datetime.combine(self.date, time(23, 59, 59), tzinfo=pytz.UTC))
            & Q(to_detail__isnull=False)
            & Q(from_detail__isnull=True)
            & Q(
                Q(currency__symbol="EUR") & Q(to_detail__transaction_type=TransactionType.DEPOSIT)
                | Q(to_detail__transaction_label=TransactionLabel.MINING)
            )
        )

        deposits = Decimal(0)
        last_snapshot = Snapshot.objects.filter(date__lt=self.date).order_by("-date").first()
        if last_snapshot is None:
            # First snapshot; Simply take all predating deposits
            deposits_qs = TransactionDetail.objects.filter(deposits_filter)
        else:
            # n:th snapshot; Sum deposits of last snapshot to the deposits in period between this and last snapshot
            deposits += last_snapshot.deposits
            deposits_filter &= Q(
                tx_timestamp__gt=datetime.combine(last_snapshot.date, time(23, 59, 59), tzinfo=pytz.UTC)
            )
            deposits_qs = TransactionDetail.objects.filter(deposits_filter)
        deposits += deposits_qs.annotate(worth=CoalesceZero(F("quantity") * F("cost_basis"))).aggregate(
            sum_deposits_worth=Sum("worth")
        )["sum_deposits_worth"] or Decimal(0)

        self.worth = sum_worth
        self.cost_basis = sum_cost_basis
        self.deposits = deposits
        self.save()


class SnapshotBalance(models.Model):
    """
    Snapshot of a currency's balance for a user
    One object is generated per day transactions are made per currency
    """

    snapshot = models.ForeignKey(to=Snapshot, on_delete=models.CASCADE, related_name="balances")
    currency = models.ForeignKey(to="Currency", on_delete=models.CASCADE, related_name="snapshots")
    quantity = TransactionDecimalField(null=True, blank=True)
    cost_basis = TransactionDecimalField(null=True, blank=True)

    def __str__(self):
        return f"Snapshot Balance for {self.currency} on {self.snapshot.date}"

    def __repr__(self):
        return (
            f"<{self.__class__.__name__} ({self.pk}): {self.currency.symbol}, {self.quantity}, {self.snapshot.date})>"
        )
