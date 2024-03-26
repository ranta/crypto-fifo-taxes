from django.views.generic import TemplateView

from crypto_fifo_taxes.models import Snapshot, Transaction


class ManagementView(TemplateView):
    template_name = "management.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        latest_tx = Transaction.objects.order_by("-timestamp").first()
        if latest_tx is not None:
            context["latest_transaction_timestamp"] = str(latest_tx.timestamp)

            if latest_tx.from_detail is not None:
                latest_currency = latest_tx.from_detail.currency
            else:
                latest_currency = latest_tx.to_detail.currency

            latest_price = latest_currency.prices.order_by("-date").first()
            if latest_price is not None:
                context["latest_currency_price_date"] = str(latest_price.date)

        latest_snapshot = Snapshot.objects.order_by("-date").first()
        if latest_snapshot is not None:
            context["latest_snapshot_timestamp"] = str(latest_snapshot.date)

        return context
