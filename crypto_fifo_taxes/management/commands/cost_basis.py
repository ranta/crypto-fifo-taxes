import logging
import sys
from datetime import datetime

from django.core.management import BaseCommand
from django.db.models import Q, QuerySet

from crypto_fifo_taxes.models import Transaction
from crypto_fifo_taxes.utils.common import log_progress
from crypto_fifo_taxes.utils.wrappers import print_time_elapsed

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--fast", type=int)
        parser.add_argument("-d", "--date", type=str, help="Start from this date. Format: YYYY-MM-DD")

    @staticmethod
    @print_time_elapsed
    def calculate_cost_bases(transactions: QuerySet[Transaction]):
        count = transactions.count()

        i: int
        transaction: Transaction
        for i, transaction in enumerate(transactions):
            log_progress(f"Calculating cost basis: {transaction.timestamp.date()}", i, count, 100)
            transaction.fill_cost_basis()

    def handle(self, *args, **kwargs):
        fast_mode = kwargs.pop("fast")
        date = kwargs.pop("date")

        transactions = Transaction.objects.order_by("timestamp", "pk").defer(
            "description", "tx_id", "transaction_label"
        )

        if date:
            # Date is given, calculate cost basis for transactions after this date.
            date = datetime.strptime(date, "%Y-%m-%d").date()
            transactions = transactions.filter(timestamp__date__gte=date)
        elif fast_mode:
            # Use the first transaction that has no cost basis as a starting point
            first_tx_with_no_cost_basis = transactions.filter(
                Q(from_detail__isnull=False) & Q(from_detail__cost_basis__isnull=True)
                | Q(to_detail__isnull=False) & Q(to_detail__cost_basis__isnull=True)
                | Q(fee_detail__isnull=False) & Q(fee_detail__cost_basis__isnull=True)
            ).first()

            if first_tx_with_no_cost_basis is None:
                logger.info("All transactions cost basis has been calculated, nothing to do.")
                return

            logger.info(f"Calculating cost basis for starting from {first_tx_with_no_cost_basis.timestamp}.")
            transactions = transactions.filter(timestamp__gte=first_tx_with_no_cost_basis.timestamp)
        else:
            # Date is not given and fast mode is not enabled, calculate cost basis for all transactions.
            logger.info("Calculating cost basis for ALL transactions.")

        transactions = transactions.select_related(
            "from_detail",
            "to_detail",
            "fee_detail",
            "from_detail__currency",
            "to_detail__currency",
            "fee_detail__currency",
            "from_detail__wallet",
        )
        self.calculate_cost_bases(transactions)
