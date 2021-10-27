from django.db.models import F, Sum
from django.views.generic import ListView

from crypto_fifo_taxes.enums import TransactionLabel
from crypto_fifo_taxes.models import Transaction


class TransactionListView(ListView):
    model = Transaction
    queryset = (
        Transaction.objects.annotate(profit=F("gain") - F("fee_amount"))
        .exclude(transaction_label=TransactionLabel.MINING)
        .order_by("timestamp", "pk")
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["totals"] = self.get_queryset().aggregate(
            sum_gain=Sum("gain"),
            sum_fee_amount=Sum("fee_amount"),
            sum_profit=Sum("profit"),
        )
        return context
