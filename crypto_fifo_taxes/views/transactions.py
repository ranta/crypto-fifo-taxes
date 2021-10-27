from django.db.models import F, Q, QuerySet, Sum
from django.http import QueryDict
from django.views.generic import ListView

from crypto_fifo_taxes.enums import TransactionLabel, TransactionType
from crypto_fifo_taxes.models import Transaction


class TransactionListView(ListView):
    model = Transaction

    def get_page_title(self) -> str:
        query_params: QueryDict = self.request.GET
        time = "year" in query_params and query_params["year"] and f"the year {query_params['year']}" or "all time"
        tx_type = "mining" in query_params and "Mining" or "Capital gains"
        return f"{tx_type} transactions for {time}"

    def filter_queryset(self, queryset: QuerySet[Transaction]) -> QuerySet[Transaction]:
        """
        Filter examples:
        `?year=2020`
        `?mining`  # No value needed.
        """
        query_params: QueryDict = self.request.GET
        filters = Q()

        if "year" in query_params and query_params["year"]:
            filters &= Q(timestamp__year=query_params["year"])

        if "mining" in query_params:
            filters &= Q(transaction_label=TransactionLabel.MINING)
        else:
            filters &= ~Q(transaction_label=TransactionLabel.MINING)

        return queryset.filter(filters)

    def get_queryset(self) -> QuerySet[Transaction]:
        queryset = (
            Transaction.objects
            # Exclude transfers that had no fees
            .exclude(transaction_type=TransactionType.TRANSFER, fee_amount=0, gain=0)
            .exclude(transaction_type=TransactionType.WITHDRAW, fee_amount=0, gain=0)
            .annotate(profit=F("gain") - F("fee_amount"))
            .order_by("timestamp", "pk")
        )
        return self.filter_queryset(queryset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = self.get_page_title()
        context["totals"] = self.get_queryset().aggregate(
            sum_gain=Sum("gain"),
            sum_fee_amount=Sum("fee_amount"),
            sum_profit=Sum("profit"),
        )
        return context
