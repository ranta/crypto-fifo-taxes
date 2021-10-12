from django.core.management import BaseCommand
from django.db.models import F, Sum
from django.db.transaction import atomic

from crypto_fifo_taxes.enums import TransactionLabel
from crypto_fifo_taxes.models import Transaction, Wallet
from crypto_fifo_taxes.models.transaction import TransactionQuerySet


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

        print(f"\nProfits for the year {year}: {self.get_profits(qs):.2f} {self.fiat}")
        if trades.exists():
            print(f"Trades: {self.get_profits(trades):.2f} {self.fiat}")

        if mining.exists():
            print(f"Mining: {self.get_profits(mining):.2f} {self.fiat}")

        if rewards.exists():
            print(f"Rewards: {self.get_profits(rewards):.2f} {self.fiat}")

    @atomic
    def handle(self, *args, **kwargs):
        self.year = kwargs.pop("year", None)
        self.full_mode = kwargs.pop("full", 0)
        self.symbol = kwargs.pop("symbol", None)

        years = self.get_years()

        for year in years:
            self.handle_year(year)
