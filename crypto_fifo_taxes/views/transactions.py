import datetime
from decimal import Decimal

from django.db.models import Case, DateField, F, OuterRef, Q, QuerySet, Subquery, Sum, When
from django.db.models.functions import Cast
from django.http import QueryDict
from django.views.generic import ListView

from crypto_fifo_taxes.enums import TransactionLabel, TransactionType
from crypto_fifo_taxes.exceptions import MissingCostBasisError
from crypto_fifo_taxes.models import Currency, CurrencyPrice, Transaction
from crypto_fifo_taxes.utils.db import CoalesceZero


class TransactionListView(ListView):
    model = Transaction

    def get_page_title(self) -> str:
        query_params: QueryDict = self.request.GET
        time = "all time"
        if year := query_params.get("year"):
            time = f"the year {year}"
        return f"Capital gains transactions for {time}"

    def filter_queryset(self, queryset: QuerySet[Transaction]) -> QuerySet[Transaction]:
        """
        Filter examples:
        `?year=2020`
        """
        query_params: QueryDict = self.request.GET
        filters = Q()

        year = query_params.get("year", datetime.datetime.now().year)
        filters &= Q(timestamp__year=year)

        # Exclude mining transactions
        filters &= ~Q(transaction_label=TransactionLabel.MINING)

        return queryset.filter(filters)

    def get_queryset(self) -> QuerySet[Transaction]:
        if Transaction.objects.filter(
            Q(from_detail__isnull=False, from_detail__cost_basis=None)
            | Q(to_detail__isnull=False, to_detail__cost_basis=None)
        ).exists():
            raise MissingCostBasisError("Transactions with missing cost basis exist")

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
                from_detail__total_value=Case(
                    When(
                        Q(transaction_type=TransactionType.WITHDRAW) & ~Q(transaction_label=TransactionLabel.SPENDING),
                        then=Decimal(0),
                    ),
                    default=CoalesceZero(F("from_detail__quantity") * F("from_detail__cost_basis")),
                ),
                # Add a "sell value" for `SPENDING` transactions.
                # Required to make `from_total - to_total == gains_total`
                timestamp_date=Cast("timestamp", DateField()),  # Allow filtering CurrencyPrices
                to_detail__total_value=Case(
                    When(
                        transaction_label=TransactionLabel.SPENDING,
                        then=Subquery(
                            CurrencyPrice.objects.filter(
                                date=OuterRef("timestamp_date"),
                                currency=OuterRef("from_detail__currency"),
                            ).values_list("price", flat=True)[:1]
                        )
                        * F("from_detail__quantity"),
                    ),
                    default=CoalesceZero(F("to_detail__quantity") * F("to_detail__cost_basis")),
                ),
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
        context["years"] = (
            Transaction.objects.values_list("timestamp__year", flat=True)
            .order_by("timestamp__year")
            .distinct("timestamp__year")
        )
        return context


class TransactionMiningListView(TransactionListView):
    def get_page_title(self) -> str:
        query_params: QueryDict = self.request.GET
        time = "all time"
        if year := query_params.get("year"):
            time = f"the year {year}"
        return f"Mining transactions for {time}"

    def filter_queryset(self, queryset: QuerySet[Transaction]) -> QuerySet[Transaction]:
        """
        Filter examples:
        `?year=2020`
        """
        query_params: QueryDict = self.request.GET
        filters = Q()

        if year := query_params.get("year"):
            filters &= Q(timestamp__year=year)

        # Include only mining transactions
        filters &= Q(transaction_label=TransactionLabel.MINING)

        return queryset.filter(filters)


class TransactionByCurrencyListView(ListView):
    model = Transaction
    template_name = "crypto_fifo_taxes/transaction_by_currency_list.html"

    def get_page_title(self) -> str:
        query_params: QueryDict = self.request.GET
        if currency_symbol := query_params.get("currency_symbol"):
            currency = Currency.objects.get(symbol=currency_symbol)
            return f"All transactions for {currency.name} ({currency.symbol})"
        return "Select a currency"

    def filter_queryset(self, queryset: QuerySet[Transaction]) -> QuerySet[Transaction]:
        """
        Filter examples:
        `?currency=btc`
        """
        query_params: QueryDict = self.request.GET
        if currency_symbol := query_params.get("currency_symbol"):
            return queryset.filter_currency(currency_symbol)
        else:
            return queryset.none()

    def get_queryset(self) -> QuerySet[Transaction]:
        queryset = Transaction.objects.order_by("timestamp", "pk").select_related(
            "from_detail",
            "to_detail",
            "fee_detail",
            "from_detail__currency",
            "to_detail__currency",
            "fee_detail__currency",
            "to_detail__wallet",
            "from_detail__wallet",
        )
        return self.filter_queryset(queryset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = self.get_page_title()
        context["selected_currency_symbol"] = self.request.GET.get("currency_symbol")
        context["currency_symbols"] = Currency.objects.values_list("symbol", flat=True).order_by("symbol")
        return context
