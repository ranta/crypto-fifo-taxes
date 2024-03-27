from django.views.generic import TemplateView

from crypto_fifo_taxes.models import CurrencyPrice, Snapshot, Transaction


class ManagementView(TemplateView):
    template_name = "management.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if latest_tx := Transaction.objects.order_by("-timestamp").first():
            context["latest_transaction_timestamp"] = latest_tx.timestamp.strftime("%Y-%m-%d %H:%M:%S")

        if latest_price := CurrencyPrice.objects.order_by("-date").first():
            context["latest_currency_price_date"] = str(latest_price.date)

        if latest_snapshot := Snapshot.objects.order_by("-date").first():
            context["latest_snapshot_timestamp"] = str(latest_snapshot.date)

        context["unprocessed_transactions_count"] = Transaction.objects.filter(gain=None).count()

        return context
