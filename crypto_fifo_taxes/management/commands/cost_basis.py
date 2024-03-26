import logging
import sys
from datetime import datetime

from django.core.management import BaseCommand
from django.db.models import Q, QuerySet

from crypto_fifo_taxes.models import Transaction
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
            logger.info(f"Calculating cost bases. {(i + 1) / count * 100:>5.2f}% ({transaction.timestamp.date()})")
            transaction.fill_cost_basis()

    def handle(self, *args, **kwargs):
        fast_mode = kwargs.pop("fast")
        date = kwargs.pop("date")

        if date:
            # Date is given, calculate cost basis for transactions after this date.
            date = datetime.strptime(date, "%Y-%m-%d").date()
            transactions = Transaction.objects.order_by("timestamp", "pk").filter(timestamp__date__gte=date)
        elif fast_mode:
            # Use the first transaction that has no cost basis as a starting point
            first_tx_with_no_cost_basis = (
                Transaction.objects.filter(
                    Q(from_detail__isnull=False) & Q(from_detail__cost_basis__isnull=True)
                    | Q(to_detail__isnull=False) & Q(to_detail__cost_basis__isnull=True)
                    | Q(fee_detail__isnull=False) & Q(fee_detail__cost_basis__isnull=True)
                )
                .order_by("timestamp", "pk")
                .first()
            )

            if first_tx_with_no_cost_basis is None:
                logger.info("All transactions cost basis has been calculated, nothing to do.")
                return

            logger.info(f"Calculating cost basis for starting from {first_tx_with_no_cost_basis.timestamp}.")
            transactions = Transaction.objects.order_by("timestamp", "pk").filter(
                timestamp__gte=first_tx_with_no_cost_basis.timestamp
            )
        else:
            # Date is not given and fast mode is not enabled, calculate cost basis for all transactions.
            logger.info("Calculating cost basis for ALL transactions.")
            transactions = Transaction.objects.all().order_by("timestamp", "pk")

        self.calculate_cost_bases(transactions)
