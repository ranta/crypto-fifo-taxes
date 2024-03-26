from django.shortcuts import redirect
from django.urls import reverse
from django.views import View

from crypto_fifo_taxes.utils.helpers.snapshot_helper import SnapshotHelper


class BaseCommandView(View):
    http_method_names = ["post"]

    def post(self, request):
        self.handle_command()
        return redirect(reverse("management"))

    def handle_command(self):
        raise NotImplementedError


class FetchTransactionsView(BaseCommandView):
    def handle_command(self):
        pass


class FetchPricesView(BaseCommandView):
    def handle_command(self):
        pass


class CalculateSnapshotsView(BaseCommandView):
    def handle_command(self):
        snapshot_helper = SnapshotHelper()
        snapshot_helper.generate_snapshots()
        snapshot_helper.generate_snapshot_balances()
        snapshot_helper.calculate_snapshots_worth()
