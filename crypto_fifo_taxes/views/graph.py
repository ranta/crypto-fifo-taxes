import json
from datetime import datetime, time

from django.db.models import FloatField
from django.db.models.functions import Cast
from django.http import HttpResponse
from django.template import loader

from crypto_fifo_taxes.models import Snapshot


def snapshot_graph(request):
    snapshot_worth = (
        Snapshot.objects.order_by("date")
        .annotate(worth_float=Cast("worth", FloatField()))
        .values_list("worth_float", flat=True)
    )

    snapshot_cost_basis = (
        Snapshot.objects.order_by("date")
        .annotate(cost_basis_float=Cast("cost_basis", FloatField()))
        .values_list("cost_basis_float", flat=True)
    )

    template = loader.get_template("graph.html")
    context = {
        "point_start": datetime.combine(Snapshot.objects.order_by("date").first().date, time()).timestamp() * 1000,
        "snapshot_worth": json.dumps(list(snapshot_worth)),
        "snapshot_cost_basis": json.dumps(list(snapshot_cost_basis)),
    }
    return HttpResponse(template.render(context, request))
