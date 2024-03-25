from django.shortcuts import redirect
from django.urls import reverse
from django.views import View


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
        pass
