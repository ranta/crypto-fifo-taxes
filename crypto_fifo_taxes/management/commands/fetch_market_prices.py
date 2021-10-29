from datetime import datetime

from django.core.management import BaseCommand
from django.db.models import QuerySet

from crypto_fifo_taxes.models import Currency, Snapshot, Transaction
from crypto_fifo_taxes.utils.coingecko import fetch_currency_market_chart
from crypto_fifo_taxes.utils.wrappers import print_time_elapsed


class Command(BaseCommand):
    first_date = None

    def add_arguments(self, parser):
        parser.add_argument("-d", "--date", type=str, help="Start from this date. Format: YYYY-MM-DD")

    def get_required_currencies(self) -> QuerySet[Currency]:
        """Get all currencies owned at any point after the start_date"""

        # Currencies in latest snapshot
        latest_snapshot = Snapshot.objects.filter(date__lte=self.date).order_by("-date").first()
        snapshot_currency_ids = []
        if latest_snapshot is not None:
            snapshot_currency_ids = latest_snapshot.get_balances().values_list("currency_id", flat=True)

        # Currencies used in future transactions
        tx_currency_ids = (
            Transaction.objects.filter(timestamp__date__gte=self.date)
            .values_list("from_detail__currency_id", "to_detail__currency_id")
            .distinct()
        )

        # Combine Currencies from latest snapshot and future transactions into a set
        currency_ids = set(sum([list(c_tuple) for c_tuple in tx_currency_ids], list(snapshot_currency_ids)))

        return Currency.objects.filter(pk__in=currency_ids, is_fiat=False)

    @print_time_elapsed
    def fetch_historical_market_prices(self):
        currencies = self.get_required_currencies()
        count = currencies.count()
        print(f"Fetching market data for {count} currencies: {', '.join(currencies.values_list('symbol', flat=True))}")
        for i, currency in enumerate(currencies):
            print(f"Fetching market chart prices for {currency.symbol} {(i + 1) / count * 100:>5.2f}%", end="\r")
            fetch_currency_market_chart(currency, start_date=self.date)

    def handle(self, *args, **kwargs):
        self.mode = kwargs.pop("mode", None)
        self.date = kwargs.pop("date", None)

        if self.date is not None:
            self.date = datetime.strptime(self.date, "%Y-%m-%d").date()
        else:
            self.date = Transaction.objects.order_by("timestamp").first().timestamp.date()

        self.fetch_historical_market_prices()
