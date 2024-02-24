import logging
import sys

from django.core.management import BaseCommand

from crypto_fifo_taxes.models import Currency
from crypto_fifo_taxes.utils.coingecko import fetch_currency_market_chart
from crypto_fifo_taxes.utils.wrappers import print_time_elapsed

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    @print_time_elapsed
    def fetch_historical_market_prices(self):
        currency_qs = Currency.objects.filter(is_fiat=False)
        count = currency_qs.count()
        logger.info(
            f"Fetching market data for {count} currencies: ({', '.join(currency_qs.values_list('symbol', flat=True))})"
        )
        for i, currency in enumerate(currency_qs):
            logger.info(f"Fetching market data for {currency.symbol} {(i + 1) / count * 100:>5.2f}% ({i+1}/{count})")
            fetch_currency_market_chart(currency)

    def handle(self, *args, **kwargs):
        self.mode = kwargs.pop("mode", None)

        self.fetch_historical_market_prices()
