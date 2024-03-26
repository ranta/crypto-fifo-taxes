import logging
from typing import Any

from django.conf import settings
from django.db import models

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

    def get_balances(self) -> list[dict[str, Any]]:
        """Return the last calculated snapshot balance for user"""
        values_qs = (
            SnapshotBalance.objects.filter(snapshot__date__lte=self.date)
            .order_by("currency_id", "-snapshot__date")
            .distinct("currency_id")
            .values("currency_id", "currency__symbol", "quantity", "cost_basis")
        )

        return [c for c in values_qs if c["quantity"] != 0]


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
