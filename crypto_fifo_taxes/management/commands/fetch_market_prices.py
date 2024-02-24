import itertools
import logging
from datetime import datetime

from django.conf import settings
from django.core.management import BaseCommand
from django.db.models import QuerySet

from crypto_fifo_taxes.models import Currency, Snapshot, Transaction
from crypto_fifo_taxes.utils.coingecko import fetch_currency_market_chart
from crypto_fifo_taxes.utils.wrappers import print_time_elapsed

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    first_date = None

    def add_arguments(self, parser):
        parser.add_argument("-d", "--date", type=str, help="Start from this date. Format: YYYY-MM-DD")

    def get_required_currencies(self) -> QuerySet[Currency]:
        """Get all currencies owned in the latest snapshot and ones traded after the start_date"""
        # Currencies in latest snapshot
        latest_snapshot = Snapshot.objects.filter(date__lte=self.start_date).order_by("-date").first()
        snapshot_currency_ids = []
        if latest_snapshot is not None:
            snapshot_currency_ids = [
                currency["currency_id"] for currency in latest_snapshot.get_balances(include_zero_balances=False)
            ]

        # Currencies used in future transactions
        tx_detail_currency_ids = (
            Transaction.objects.filter(timestamp__date__gte=self.start_date)
            .order_by("from_detail__currency_id", "to_detail__currency_id")
            .values_list("from_detail__currency_id", "to_detail__currency_id")
            .distinct()
        )
        # Flatten the list of tuples
        tx_currency_ids = list(itertools.chain(*tx_detail_currency_ids))

        # Combine Currencies from latest snapshot and future transactions into a set
        currency_ids = {*tx_currency_ids, *snapshot_currency_ids}

        # Remove excluded symbols from the set
        excluded_symbols = set(
            [k.upper() for k in settings.DEPRECATED_TOKENS]
            + settings.COINGECKO_ASSUME_ZERO_PRICE_TOKENS
            + settings.IGNORED_TOKENS
            + [None]
        )
        currency_ids = currency_ids - excluded_symbols

        return Currency.objects.filter(pk__in=currency_ids, is_fiat=False)

    @print_time_elapsed
    def fetch_historical_market_prices(self):
        currencies = self.get_required_currencies()
        count = currencies.count()
        logger.info(
            f"Fetching market data starting from {self.start_date} for {count} currencies: "
            f"{', '.join(currencies.values_list('symbol', flat=True))}"
        )
        for i, currency in enumerate(currencies):
            logger.info(f"Fetching market data for {currency.symbol} {(i + 1) / count * 100:>5.2f}% ({i+1}/{count})")
            first_transaction_date = currency.transaction_details.order_by("tx_timestamp").first()
            if first_transaction_date is not None:
                first_transaction_date = first_transaction_date.tx_timestamp.date()
            fetch_currency_market_chart(currency, start_date=first_transaction_date or self.start_date)

    def handle(self, *args, **kwargs):
        self.mode = kwargs.pop("mode", None)
        self.date = kwargs.pop("date", None)

        if self.date is not None:
            self.start_date = datetime.strptime(self.date, "%Y-%m-%d").date()
        else:
            self.start_date = Transaction.objects.order_by("timestamp").first().timestamp.date()

        self.fetch_historical_market_prices()
