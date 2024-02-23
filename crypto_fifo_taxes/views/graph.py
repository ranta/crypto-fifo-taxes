import json
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from django.db.models import Case, DecimalField, ExpressionWrapper, F, FloatField, OuterRef, Q, QuerySet, Subquery, When
from django.db.models.functions import Cast
from django.http import QueryDict
from django.views.generic import TemplateView

from crypto_fifo_taxes.models import CurrencyPrice, Snapshot
from crypto_fifo_taxes.utils.currency import get_currency, get_default_fiat
from crypto_fifo_taxes.utils.db import CoalesceZero


def jdl(qs: QuerySet[Any]):
    return json.dumps(list(qs))


def qs_values_list_to_float(qs, field) -> QuerySet[Any]:
    """Cast a field's type to Float to make it work better with `json.dumps`, then output field values as a list"""
    return qs.annotate(float_field=Cast(field, FloatField())).values_list("float_field", flat=True)


class GraphView(TemplateView):
    template_name = "graph.html"

    def get_starting_date(self) -> date:
        """Usage: `?start=2020-1-1`"""
        first_snapshot_date = Snapshot.objects.order_by("date").first().date

        query_params: QueryDict = self.request.GET
        if query_params.get("start"):
            return max(datetime.strptime(query_params["start"], "%Y-%m-%d").date(), first_snapshot_date)
        return first_snapshot_date

    def filter_queryset(self, queryset: QuerySet[Snapshot, CurrencyPrice]) -> QuerySet[Snapshot, CurrencyPrice]:
        filters = Q()
        filters &= Q(date__gte=self.get_starting_date())
        return queryset.filter(filters)

    # Currency prices
    def currency_price_returns(self, symbol) -> QuerySet[CurrencyPrice]:
        qs = CurrencyPrice.objects.filter(fiat=get_default_fiat(), currency=get_currency(symbol)).order_by("date")
        qs = self.filter_queryset(qs)
        first_price = qs.first().price

        return qs.annotate(
            returns=ExpressionWrapper((F("price") - first_price) / first_price * 100, output_field=FloatField()),
        ).values_list("returns", flat=True)

    def currency_price_values_list(self, symbol) -> QuerySet[CurrencyPrice]:
        qs = CurrencyPrice.objects.filter(fiat=get_default_fiat(), currency=get_currency(symbol)).order_by("date")
        qs = self.filter_queryset(qs)
        return qs_values_list_to_float(qs, "price")

    # Wallet prices
    def get_snapshot_worth(self) -> str:
        return jdl(
            qs_values_list_to_float(
                qs=Snapshot.objects.filter(date__gte=self.get_starting_date()),
                field="worth",
            )
        )

    def get_snapshot_cost_basis(self) -> str:
        return jdl(
            qs_values_list_to_float(
                qs=Snapshot.objects.filter(date__gte=self.get_starting_date()),
                field="cost_basis",
            )
        )

    # Wallet returns
    def get_total_returns(self) -> str:
        try:
            past = Snapshot.objects.filter(date__lt=self.get_starting_date()).order_by("-date").first()
            past = past.worth - past.deposits
        except AttributeError:
            past = 0

        qs = (
            Snapshot.objects.filter(date__gte=self.get_starting_date())
            .order_by("date")
            .annotate(
                returns=Case(
                    # Avoid division by zero
                    When(deposits=Decimal(0), then=Decimal(0)),
                    # When(deposits=past_deposits, then=Decimal(0)),
                    default=ExpressionWrapper(
                        (F("worth") - F("deposits") - past) / (F("deposits")) * 100,
                        output_field=DecimalField(),
                    ),
                    output_field=FloatField(),
                ),
            )
            .values_list("returns", flat=True)
        )
        return jdl(qs)

    def get_time_weighted_returns(self):
        def cumulative_product(lst):
            results = []
            cur = 1
            for n in lst:
                cur *= n
                results.append((cur - 1) * 100)
            return results

        qs = (
            Snapshot.objects.filter(date__gte=self.get_starting_date())
            .annotate(
                deposits_delta=ExpressionWrapper(
                    F("deposits")
                    - CoalesceZero(
                        Subquery(
                            Snapshot.objects.filter(date__lt=OuterRef("date"))
                            .order_by("-date")
                            .values_list("deposits")[:1]
                        )
                    ),
                    output_field=DecimalField(),
                ),
                last_worth=CoalesceZero(
                    Subquery(
                        Snapshot.objects.filter(date__lt=OuterRef("date")).order_by("-date").values_list("worth")[:1]
                    ),
                ),
                twr_returns=ExpressionWrapper(
                    1
                    + (F("worth") - (F("last_worth") + F("deposits_delta"))) / (F("last_worth") + F("deposits_delta")),
                    output_field=FloatField(),
                ),
            )
            .values_list("twr_returns", flat=True)
        )
        return cumulative_product(qs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        starting_point = datetime.combine(self.get_starting_date(), time()).timestamp() * 1000
        context["point_start"] = starting_point

        # Legends
        context["graphs"] = [
            {"name": "Portfolio Values", "data": [], "suffix": "", "id": "portfolio_abs"},
            {"name": "Portfolio Returns", "data": [], "suffix": "", "id": "portfolio_per"},
            {"name": "Currency Prices", "data": [], "suffix": "", "id": "currency_abs"},
            {"name": "Currency Returns", "data": [], "suffix": "", "id": "currency_per"},
        ]

        # Graph data
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

        # Currencies
        currencies = ["btc", "eth"]
        for symbol in currencies:
            context["graphs"].append(
                {
                    "linked_to": "currency_abs",
                    "name": f"{symbol.upper()} Price",
                    "data": jdl(self.currency_price_values_list(symbol)),
                    "suffix": "€",
                }
            )
        for symbol in currencies:
            context["graphs"].append(
                {
                    "linked_to": "currency_per",
                    "name": f"{symbol.upper()} Returns",
                    "data": jdl(self.currency_price_returns(symbol)),
                    "suffix": "%",
                }
            )

        return context
