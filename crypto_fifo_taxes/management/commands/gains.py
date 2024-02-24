import logging
import sys
from datetime import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management import BaseCommand
from django.db.models import F, Sum
from django.db.transaction import atomic

from crypto_fifo_taxes.enums import TransactionLabel, TransactionType
from crypto_fifo_taxes.models import Transaction, Wallet
from crypto_fifo_taxes.models.transaction import TransactionDetail, TransactionQuerySet
from crypto_fifo_taxes.utils.currency import get_currency
from crypto_fifo_taxes.utils.wallet import get_wallet_balance_sum

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    fiat = Wallet.objects.first().fiat.symbol

    def add_arguments(self, parser):
        parser.add_argument("--year", type=str)
        parser.add_argument("--full", type=int)
        parser.add_argument("--symbol", type=str)

    def get_years(self) -> list:
        if self.year is None:
            return list(
                Transaction.objects.all()
                .distinct()
                .values_list("timestamp__year", flat=True)
                .order_by("timestamp__year")
                .distinct()
            )
        return [self.year]

    def get_base_qs(self) -> TransactionQuerySet:
        base_qs = (
            Transaction.objects.annotate(profit=F("gain") - F("fee_amount"))
            .exclude(profit=0)
            .order_by("timestamp", "pk")
        )
        if self.symbol is not None:
            base_qs = base_qs.filter_currency(self.symbol)
        return base_qs

    @staticmethod
    def get_profits(qs):
        return qs.aggregate(sum=Sum("profit"))["sum"]

    def handle_year(self, year):
        qs = self.get_base_qs().filter(timestamp__year=year)

        if not qs.exists():
            return

        trades = qs.filter(transaction_label=TransactionLabel.UNKNOWN)
        mining = qs.filter(transaction_label=TransactionLabel.MINING)
        rewards = qs.filter(transaction_label=TransactionLabel.REWARD)

        logger.info(f"\nProfits for the year {year}: {self.get_profits(qs):.2f} {self.fiat}")
        if trades.exists():
            logger.info(f"Trades: {self.get_profits(trades):.2f} {self.fiat}")

        if mining.exists():
            logger.info(f"Mining: {self.get_profits(mining):.2f} {self.fiat}")

        if rewards.exists():
            logger.info(f"Rewards: {self.get_profits(rewards):.2f} {self.fiat}")

    @atomic
    def handle(self, *args, **kwargs):
        self.year = kwargs.pop("year", None)
        self.full_mode = kwargs.pop("full", 0)
        self.symbol = kwargs.pop("symbol", None)

        years = self.get_years()

        for year in years:
            self.handle_year(year)

        deposits = (
            TransactionDetail.objects.filter(to_detail__transaction_type=TransactionType.DEPOSIT)
            .exclude(to_detail__transaction_label=TransactionLabel.REWARD)
            .annotate(cost=F("cost_basis") * F("quantity"))
            .aggregate(sum=Sum("cost"))["sum"]
        )
        withdrawals = (
            TransactionDetail.objects.filter(from_detail__transaction_type=TransactionType.WITHDRAW)
            .annotate(cost=F("cost_basis") * F("quantity"))
            .aggregate(sum=Sum("cost"))["sum"]
        )

        combined_wallet_balance = get_wallet_balance_sum(User.objects.first())
        total_wallet_sum = Decimal()
        for symbol, quantity in combined_wallet_balance.items():
            currency = get_currency(symbol)
            if currency.is_fiat:
                total_wallet_sum += quantity
                continue
            price = currency.get_fiat_price(date=datetime.now().date()).price
            total_wallet_sum += price

        logger.info(f"\nDeposits {deposits}")
        logger.info(f"Withdrawals {withdrawals}")
        logger.info(f"Current wallet balance {total_wallet_sum}")
        logger.info(f"Profit € {(withdrawals + total_wallet_sum) - deposits}")
        logger.info(f"Profit % {((withdrawals + total_wallet_sum) / deposits - 1) * 100}%")
