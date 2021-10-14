from django.db.models import F, Sum
from django.http import HttpResponse
from django.template import loader

from crypto_fifo_taxes.enums import TransactionLabel
from crypto_fifo_taxes.models import Transaction


def transaction_list(request):
    transaction_list = (
        Transaction.objects.annotate(profit=F("gain") - F("fee_amount"))
        .exclude(transaction_label=TransactionLabel.MINING)
        .order_by("timestamp", "pk")
    )
    totals = transaction_list.aggregate(
        sum_gain=Sum("gain"), sum_fee_amount=Sum("fee_amount"), sum_profit=Sum("profit")
    )
    template = loader.get_template("transactions.html")
    context = {"transaction_list": transaction_list, "totals": totals}
    return HttpResponse(template.render(context, request))
