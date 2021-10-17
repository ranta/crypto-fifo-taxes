import json
from datetime import datetime, time
from decimal import Decimal

from django.db.models import Case, DecimalField, ExpressionWrapper, F, FloatField, When
from django.db.models.functions import Cast
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

    snapshot_worth = qs_values_list_to_float(qs=Snapshot.objects.all(), field="worth")
    snapshot_cost_basis = qs_values_list_to_float(qs=Snapshot.objects.all(), field="cost_basis")
    bitcoin_price = currency_price_values_list(symbol="BTC")
    ethereum_price = currency_price_values_list(symbol="ETH")
    btc_time_weighted_returns = currency_price_twr("BTC")
    eth_time_weighted_returns = currency_price_twr("ETH")

    time_weighted_returns = (
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

    template = loader.get_template("graph.html")
    context = {
        "point_start": datetime.combine(Snapshot.objects.order_by("date").first().date, time()).timestamp() * 1000,
        "snapshot_worth": jdl(snapshot_worth),
        "snapshot_cost_basis": jdl(snapshot_cost_basis),
        "bitcoin_price": jdl(bitcoin_price),
        "ethereum_price": jdl(ethereum_price),
        "btc_time_weighted_returns": jdl(btc_time_weighted_returns),
        "eth_time_weighted_returns": jdl(eth_time_weighted_returns),
        "time_weighted_returns": jdl(time_weighted_returns),
    }
    return HttpResponse(template.render(context, request))
