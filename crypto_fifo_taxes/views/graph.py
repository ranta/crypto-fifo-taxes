import json
from datetime import datetime, time
from decimal import Decimal

from django.db.models import Case, DecimalField, ExpressionWrapper, F, FloatField, OuterRef, Subquery, When
from django.db.models.functions import Cast, Coalesce
from django.http import HttpResponse
from django.template import loader

from crypto_fifo_taxes.models import CurrencyPrice, Snapshot
from crypto_fifo_taxes.utils.currency import get_currency, get_default_fiat


def snapshot_graph(request):
    def jdl(qs):
        return json.dumps(list(qs))

    def qs_values_list_to_float(qs, field):
        return qs.annotate(float_field=Cast(field, FloatField())).values_list("float_field", flat=True)

    def currency_price_values_list(symbol):
        qs = CurrencyPrice.objects.filter(fiat=get_default_fiat(), currency=get_currency(symbol)).order_by("date")
        return qs_values_list_to_float(qs, "price")

    def currency_price_twr(symbol):
        qs = CurrencyPrice.objects.filter(fiat=get_default_fiat(), currency=get_currency(symbol)).order_by("date")
        first_price = qs.first().price

        return qs.annotate(
            twr=ExpressionWrapper((F("price") - first_price) / first_price * 100, output_field=FloatField()),
        ).values_list("twr", flat=True)

    def cumulative_product(lst):
        results = []
        cur = 1
        for n in lst:
            cur *= n
            results.append((cur - 1) * 100)
        return results

    snapshot_worth = qs_values_list_to_float(qs=Snapshot.objects.all(), field="worth")
    snapshot_cost_basis = qs_values_list_to_float(qs=Snapshot.objects.all(), field="cost_basis")
    bitcoin_price = currency_price_values_list(symbol="BTC")
    ethereum_price = currency_price_values_list(symbol="ETH")
    btc_returns = currency_price_twr("BTC")
    eth_returns = currency_price_twr("ETH")

    total_returns = (
        Snapshot.objects.order_by("date")
        .annotate(
            twr=Case(
                # Avoid division by zero
                When(deposits=Decimal(0), then=Decimal(0)),
                default=ExpressionWrapper(
                    (F("worth") - F("deposits")) / F("deposits") * 100, output_field=DecimalField()
                ),
                output_field=FloatField(),
            ),
        )
        .values_list("twr", flat=True)
    )

    time_weighted_returns = Snapshot.objects.annotate(
        deposits_delta=ExpressionWrapper(
            F("deposits")
            - Coalesce(
                Subquery(
                    Snapshot.objects.filter(date__lt=OuterRef("date")).order_by("-date").values_list("deposits")[:1]
                ),
                0,
                output_field=DecimalField(),
            ),
            output_field=DecimalField(),
        ),
        last_worth=Coalesce(
            Subquery(Snapshot.objects.filter(date__lt=OuterRef("date")).order_by("-date").values_list("worth")[:1]),
            0,
            output_field=DecimalField(),
        ),
        twr=ExpressionWrapper(
            1 + (F("worth") - (F("last_worth") + F("deposits_delta"))) / (F("last_worth") + F("deposits_delta")),
            output_field=FloatField(),
        ),
    ).values_list("twr", flat=True)

    template = loader.get_template("graph.html")
    context = {
        "point_start": datetime.combine(Snapshot.objects.order_by("date").first().date, time()).timestamp() * 1000,
        "snapshot_worth": jdl(snapshot_worth),
        "snapshot_cost_basis": jdl(snapshot_cost_basis),
        "bitcoin_price": jdl(bitcoin_price),
        "ethereum_price": jdl(ethereum_price),
        "btc_returns": jdl(btc_returns),
        "eth_returns": jdl(eth_returns),
        "total_returns": jdl(total_returns),
        "time_weighted_returns": jdl(cumulative_product(time_weighted_returns)),
    }
    return HttpResponse(template.render(context, request))
