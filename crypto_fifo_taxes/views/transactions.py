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
        if Transaction.objects.filter(
            Q(from_detail__isnull=False) & Q(from_detail__cost_basis=None)
            | Q(to_detail__isnull=False) & Q(to_detail__cost_basis=None)
        ).exists():
            raise Exception("Transactions with missing cost basis exist")

        queryset = (
            Transaction.objects
            # Exclude transactions that don't affect gains/profits
            .exclude(transaction_type=TransactionType.DEPOSIT, to_detail__currency__is_fiat=True, fee_amount=0)
            .exclude(transaction_type=TransactionType.DEPOSIT, transaction_label=TransactionLabel.REWARD, gain=0)
            .exclude(transaction_type=TransactionType.TRANSFER, fee_amount=0, gain=0)
            .exclude(transaction_type=TransactionType.WITHDRAW, fee_amount=0, gain=0)
            .exclude(transaction_type=TransactionType.SWAP, fee_amount=0, gain=0)
            .annotate(
                profit=F("gain") - F("fee_amount"),
                from_detail__total_value=F("from_detail__quantity") * F("from_detail__cost_basis"),
                to_detail__total_value=F("to_detail__quantity") * F("to_detail__cost_basis"),
            )
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
            sum_from_value=Sum("from_detail__total_value"),
            sum_to_value=Sum("to_detail__total_value"),
        )
        return context
