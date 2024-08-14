import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from django.db.models import Case, DecimalField, ExpressionWrapper, F, FloatField, OuterRef, QuerySet, Subquery, When
from django.db.models.functions import Cast
from django.http import QueryDict
from django.views.generic import TemplateView

from crypto_fifo_taxes.models import CurrencyPrice, Snapshot, Transaction
from crypto_fifo_taxes.utils.currency import get_currency
from crypto_fifo_taxes.utils.date_utils import utc_start_of_day
from crypto_fifo_taxes.utils.db import CoalesceZero


def json_dumps(qs: QuerySet[Any]) -> str:
    return json.dumps(list(qs))


def qs_values_list_to_float(qs, field) -> str:
    """Cast a field's type to Float to make it work better with `json.dumps`, then output field values as a list"""
    return json_dumps(qs.annotate(float_field=Cast(field, FloatField())).values_list("float_field", flat=True))


# TODO: Ignore all fiat deposit and withdrawals transactions in the graph
class GraphView(TemplateView):
    template_name = "graph.html"

    starting_date: date
    snapshot_qs: QuerySet[Snapshot]
    base_currency_price_qs: QuerySet[CurrencyPrice]

    # Portfolio prices
    def get_snapshot_worth(self) -> str:
        return qs_values_list_to_float(qs=self.snapshot_qs, field="worth")

    def get_snapshot_cost_basis(self) -> str:
        return qs_values_list_to_float(qs=self.snapshot_qs, field="cost_basis")

    # Wallet returns
    def get_total_returns(self) -> str:
        past_snapshot = Snapshot.objects.filter(date__lt=self.starting_date).order_by("-date").first()
        past_gains = 0 if past_snapshot is None else past_snapshot.worth - past_snapshot.deposits

        qs = self.snapshot_qs.annotate(
            returns=Case(
                # Avoid division by zero
                When(deposits=Decimal(0), then=Decimal(0)),
                # When(deposits=past_deposits, then=Decimal(0)),
                default=ExpressionWrapper(
                    (F("worth") - F("deposits") - past_gains) / (F("deposits")) * 100,
                    output_field=DecimalField(),
                ),
                output_field=FloatField(),
            ),
        ).values_list("returns", flat=True)
        return json_dumps(qs)

    def get_time_weighted_returns(self):
        def cumulative_product(lst):
            results = []
            cur = 1
            for n in lst:
                cur *= n
                results.append((cur - 1) * 100)
            return results

        subquery_qs = Snapshot.objects.filter(date__lt=OuterRef("date")).order_by("-date")
        qs = (
            self.snapshot_qs.alias(
                deposits_delta=ExpressionWrapper(
                    F("deposits") - CoalesceZero(Subquery(subquery_qs.values_list("deposits")[:1])),
                    output_field=DecimalField(),
                ),
                last_worth=CoalesceZero(Subquery(subquery_qs.values_list("worth")[:1])),
            )
            .annotate(
                twr_returns=ExpressionWrapper(
                    1
                    + (F("worth") - (F("last_worth") + F("deposits_delta"))) / (F("last_worth") + F("deposits_delta")),
                    output_field=FloatField(),
                ),
            )
            .values_list("twr_returns", flat=True)
        )
        return cumulative_product(qs)

    # Currency prices
    def currency_price_returns(self, symbol) -> str:
        qs = self.base_currency_price_qs.filter(currency=get_currency(symbol))
        first_price = qs.first().price

        return json_dumps(
            qs.annotate(
                returns=ExpressionWrapper((F("price") - first_price) / first_price * 100, output_field=FloatField()),
            ).values_list("returns", flat=True)
        )

    def currency_price_values_list(self, symbol) -> str:
        qs = self.base_currency_price_qs.filter(currency=get_currency(symbol))
        return qs_values_list_to_float(qs, "price")

    def _get_starting_date(self) -> date:
        """Usage: `?start=2020-1-1`"""
        first_snapshot_date = Snapshot.objects.order_by("date").first().date

        query_params: QueryDict = self.request.GET
        if query_params.get("start"):
            first_snapshot_date = max(datetime.strptime(query_params["start"], "%Y-%m-%d").date(), first_snapshot_date)

        if Snapshot.objects.filter(date__gte=first_snapshot_date, cost_basis__isnull=True).exists():
            raise ValueError("Some snapshots are missing cost basis")

        return first_snapshot_date

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        self.starting_date = self._get_starting_date()
        self.snapshot_qs = Snapshot.objects.filter(date__gte=self.starting_date).order_by("date")
        self.base_currency_price_qs = CurrencyPrice.objects.filter(date__gte=self.starting_date).order_by("date")

        # Starting point for the graph
        starting_point = utc_start_of_day(self.starting_date).timestamp() * 1000
        context["point_start"] = starting_point

        context["years"] = (
            Transaction.objects.values_list("timestamp__year", flat=True)
            .order_by("timestamp__year")
            .distinct("timestamp__year")
        )

        # Legends
        context["graphs"] = [
            {"name": "Portfolio Values", "data": [], "suffix": "", "id": "portfolio_abs"},
            {"name": "Portfolio Returns", "data": [], "suffix": "", "id": "portfolio_per"},
            {"name": "Currency Prices", "data": [], "suffix": "", "id": "currency_abs"},
            {"name": "Currency Returns", "data": [], "suffix": "", "id": "currency_per"},
        ]

        # Portfolio graphs
        context["graphs"].extend(
            [
                {
                    "name": "Portfolio Worth",
                    "data": self.get_snapshot_worth(),
                    "suffix": "€",
                    "linked_to": "portfolio_abs",
                },
                {
                    "name": "Cost basis",
                    "data": self.get_snapshot_cost_basis(),
                    "suffix": "€",
                    "linked_to": "portfolio_abs",
                },
                {
                    "name": "Returns",
                    "data": self.get_total_returns(),
                    "suffix": "%",
                    "linked_to": "portfolio_per",
                },
                {
                    "name": "Time Weighted Returns",
                    "data": self.get_time_weighted_returns(),
                    "suffix": "%",
                    "linked_to": "portfolio_per",
                },
            ]
        )

        # Currency graphs
        currencies = ["btc", "eth"]
        for symbol in currencies:
            context["graphs"].append(
                {
                    "linked_to": "currency_abs",
                    "name": f"{symbol.upper()} Price",
                    "data": self.currency_price_values_list(symbol),
                    "suffix": "€",
                }
            )
            context["graphs"].append(
                {
                    "linked_to": "currency_per",
                    "name": f"{symbol.upper()} Returns",
                    "data": self.currency_price_returns(symbol),
                    "suffix": "%",
                }
            )

        return context
