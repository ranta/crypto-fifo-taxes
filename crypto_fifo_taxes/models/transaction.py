from __future__ import annotations

import datetime
from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Self

from django.conf import settings
from django.db import models
from django.db.models import Case, DateField, DecimalField, ExpressionWrapper, F, OuterRef, Q, Subquery, When
from django.db.models.functions import Cast, Coalesce
from django.db.transaction import atomic
from enumfields import EnumIntegerField

from crypto_fifo_taxes.enums import TransactionLabel, TransactionType
from crypto_fifo_taxes.exceptions import (
    InsufficientFundsError,
    MissingCostBasisError,
    MissingPriceHistoryError,
)
from crypto_fifo_taxes.utils.db import CoalesceZero, SQAvg, SQSum
from crypto_fifo_taxes.utils.models import TransactionDecimalField

if TYPE_CHECKING:
    from crypto_fifo_taxes.models import Currency, Wallet


class TransactionQuerySet(models.QuerySet):
    def filter_currency(self, symbol: str) -> Self:
        return self.filter(Q(from_detail__currency__symbol=symbol) | Q(to_detail__currency__symbol=symbol))


class TransactionManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related("from_detail", "to_detail", "fee_detail")


class Transaction(models.Model):
    """Contains static values for a transaction"""

    # Unique timestamp is required for each transaction, as
    # and having multiple transactions with the same timestamp will cause issues
    # In case of Transactions with the same timestamp, the transactions should be staggered by microseconds.
    timestamp = models.DateTimeField(unique=True)
    transaction_type = EnumIntegerField(TransactionType, default=TransactionType.UNKNOWN)
    transaction_label = EnumIntegerField(TransactionLabel, default=TransactionLabel.UNKNOWN)
    description = models.TextField(blank=True, default="")
    from_detail = models.OneToOneField(
        "TransactionDetail", on_delete=models.CASCADE, related_name="from_detail", null=True
    )
    to_detail = models.OneToOneField("TransactionDetail", on_delete=models.CASCADE, related_name="to_detail", null=True)
    fee_detail = models.OneToOneField(
        "TransactionDetail", on_delete=models.CASCADE, related_name="fee_detail", null=True
    )
    gain = TransactionDecimalField(null=True)  # Calculated field
    fee_amount = TransactionDecimalField(null=True)  # Calculated field

    # Used to identify imported transactions
    tx_id = models.CharField(max_length=256, blank=True, default="")

    objects = TransactionManager.from_queryset(TransactionQuerySet)()

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        if self.transaction_type == TransactionType.DEPOSIT:
            detail_str = str(self.to_detail)
        elif self.transaction_type == TransactionType.WITHDRAW:
            detail_str = str(self.from_detail)
        else:
            detail_str = f"{self.from_detail} to {self.to_detail}"
        return f"{self.transaction_type.label} of {detail_str}"

    def __repr__(self):
        return f"<{self.__class__.__name__} ({self.id}): {self}>"

    def delete(self, *args, **kwargs):
        self.from_detail.delete()
        self.to_detail.delete()
        self.fee_detail.delete()
        super().delete(*args, **kwargs)

    @staticmethod
    def _get_detail_cost_basis(
        transaction_detail: TransactionDetail, sell_price: Decimal | None = None
    ) -> tuple[Decimal, bool]:
        """
        Use FIFO to get used currency quantities and cost bases.
        Then average them and return the result

        e.g.
        Transaction consumes 5 BTC
        2 BTC has a cost basis of $100
        3 BTC has a cost basis of $150
        Cost basis for these currencies would be calculated using:
        (2 BTC * $100 + 3 BTC * $150) / 5 BTC = $130

        If it's advantageous to use deemed acquisition cost, it is used
        https://www.vero.fi/henkiloasiakkaat/omaisuus/sijoitukset/osakkeiden_myynt/
        """
        consumable_balances: TransactionDetailQuerySet = transaction_detail.get_consumable_balances()
        required_quantity: Decimal = transaction_detail.quantity
        cost_bases: list[tuple] = []  # [(quantity, cost_basis)]
        only_hmo_used = True

        def apply_hmo(balance_cost_basis):
            """
            Apply HMO only if it is advantageous to use it
            Deemed acquisition cost should be applied if the value has increased over 400%

            It is assumed that the tokens were owned for under 10 years.
            If they were owned for more than 10 years, HMO is 40% instead of 20%
            """
            if sell_price is not None and balance_cost_basis < sell_price / 5:
                return sell_price / 5
            nonlocal only_hmo_used  # Modify outer scope variable
            only_hmo_used = False
            return balance_cost_basis

        for balance in consumable_balances:
            if required_quantity == Decimal(0):
                # Nothing left to do
                break

            if balance.cost_basis is None:
                raise MissingCostBasisError(
                    f"TransactionDetail (id: {balance.id}, {balance}) is missing its `cost_basis`."
                )

            # Use the lesser of the two quantities
            # 1. If the original balance is partially used, use the remaining quantity
            # 2. Otherwise, use original quantity
            available_quantity = min(balance.quantity, balance.quantity_left)

            # Deposit has more than enough to cover the transaction, consume only what is needed.
            if required_quantity <= available_quantity:
                cost_bases.append((required_quantity, apply_hmo(balance.cost_basis)))
                required_quantity -= required_quantity
            # Deposit has less than needed, consume all of it.
            else:
                cost_bases.append((available_quantity, apply_hmo(balance.cost_basis)))
                required_quantity -= available_quantity

        if required_quantity > Decimal(0):
            raise InsufficientFundsError(
                "Transaction from detail quantity is more than wallet has available to consume! "
                f"Required: {required_quantity} {transaction_detail.currency}. "
                f"{transaction_detail.transaction.id=} {transaction_detail.id=}"
            )

        sum_quantity = sum(i for i, _ in cost_bases)
        total_value = sum(i * j for i, j in cost_bases)
        cost_basis = total_value / sum_quantity
        return Decimal(cost_basis), only_hmo_used

    def _get_from_detail_cost_basis(self, sell_price: Decimal | None = None) -> tuple[Decimal, bool]:
        return self._get_detail_cost_basis(transaction_detail=self.from_detail, sell_price=sell_price)

    def _get_fee_detail_cost_basis(self) -> Decimal:
        """TODO Use HMO for trade fees"""
        return self._get_detail_cost_basis(transaction_detail=self.fee_detail)[0]

    def _handle_buy_crypto_with_fiat_cost_basis(self) -> None:
        # from_detail cost_basis is simply the amount of FIAT it was bought with
        self.from_detail.cost_basis = Decimal(1)

        # Distribute amount of FIAT spent equally to crypto bought
        self.to_detail.cost_basis = self.from_detail.quantity / self.to_detail.quantity

    def _handle_to_sell_crypto_to_fiat_cost_basis(self) -> None:
        # Use sold price as cost basis
        self.to_detail.cost_basis = Decimal(1)

    def _handle_to_trade_crypto_to_crypto_cost_basis(self) -> None:
        # Get currency's FIAT price
        try:
            currency_value = self.to_detail.currency.get_fiat_price(self.timestamp)
            self.to_detail.cost_basis = currency_value.price
        except MissingPriceHistoryError:
            # Price was unable to be retrieved from the CoinGecko API
            # If the 'to' currency is deprecated, preserve the cost basis of the currency it was traded from
            is_deprecated = self.to_detail.currency.symbol in settings.COINGECKO_DEPRECATED_TOKENS
            is_flaky_price = self.to_detail.currency.symbol in settings.COINGECKO_FLAKY_PRICES
            if not is_deprecated and not is_flaky_price:
                raise

            calculated_from_detail_total_value = self.from_detail.quantity * self._get_from_detail_cost_basis()[0]
            self.to_detail.cost_basis = calculated_from_detail_total_value / self.to_detail.quantity

    def _handle_from_crypto_cost_basis(self) -> bool:
        # Sell value is divided for every sold token to find the average price
        sell_price = self.to_detail.total_value / self.from_detail.quantity
        from_cost_basis, only_hmo_used = self._get_from_detail_cost_basis(sell_price=sell_price)
        self.from_detail.cost_basis = from_cost_basis

        self.gain = self.to_detail.total_value - self.from_detail.total_value

        return only_hmo_used

    def _handle_transfer_or_swap_cost_basis(self) -> None:
        """
        FIXME:
        If multiple different cost_basis is present on currencies in a transfer, this changes the cost_basis of the
        coins to the average of all transferred coins. The original cost_basis shouldn't be changed on SWAP or transfer.
        This shouldn't affect the end result, except in a few very rare cases.
        """
        cost_basis = self._get_from_detail_cost_basis()[0]
        ratio = Decimal(self.from_detail.quantity / self.to_detail.quantity)

        self.from_detail.cost_basis = cost_basis

        self.to_detail.cost_basis = cost_basis * ratio

        self.gain = Decimal(0)

    def _handle_fiat_deposit_cost_basis(self) -> None:
        # If deposit is FIAT, cost basis is always 1 (1 EUR == 1 EUR)
        self.to_detail.cost_basis = Decimal(1)
        self.gain = Decimal(0)

    def _handle_deposit_cost_basis(self) -> None:
        """
        If the funds came from 'nowhere', it is always 100% gains.
        Deposits can be from e.g. Staking or Mining.
        """
        try:
            fiat_price = self.to_detail.currency.get_fiat_price(self.timestamp)
            currency_value = fiat_price.price
            self.to_detail.cost_basis = currency_value
            self.gain = currency_value * self.to_detail.quantity
        except MissingPriceHistoryError:
            # Price was unable to be retrieved from the CoinGecko API
            # If the 'to' currency is deprecated, preserve the cost basis of the currency it was traded from
            is_deprecated = self.to_detail.currency.symbol in settings.COINGECKO_DEPRECATED_TOKENS
            is_flaky_price = self.to_detail.currency.symbol in settings.COINGECKO_FLAKY_PRICES
            if not is_deprecated and not is_flaky_price:
                raise

            self.gain = Decimal(0)
            if self.from_detail:
                calculated_from_detail_total_value = self.from_detail.quantity * self._get_from_detail_cost_basis()[0]
                self.to_detail.cost_basis = calculated_from_detail_total_value / self.to_detail.quantity
            else:
                self.to_detail.cost_basis = Decimal(0)

    def _handle_fiat_withdrawal_cost_basis(self) -> None:
        """Funds are e.g. withdrawn to a bank account, which does not realize any gains."""
        self.from_detail.cost_basis = Decimal(1)
        self.gain = Decimal(0)

    def _handle_withdrawal_cost_basis(self) -> None:
        """
        Funds are sent to some third party entity (e.g. Paying for goods and services directly with crypto),
        which realizes any profits made from value appreciation (use `transfer` if moving funds between wallets)
        """
        sell_price = self.from_detail.currency.get_fiat_price(self.timestamp).price
        from_cost_basis, only_hmo_used = self._get_from_detail_cost_basis(sell_price=sell_price)
        self.from_detail.cost_basis = from_cost_basis
        self.gain = (sell_price - from_cost_basis) * self.from_detail.quantity

    def _handle_fee_cost_basis(self) -> None:
        self.fee_detail.cost_basis = self._get_fee_detail_cost_basis()

    @atomic()
    def fill_cost_basis(self) -> None:
        self.gain = None
        self.fee_amount = None

        # TODO: Refactor Cost Basis calculation to a separate helper class
        only_hmo_used = False

        # Trade / Transfer / Swap
        if self.from_detail is not None and self.to_detail is not None:
            # Trade
            if self.transaction_type == TransactionType.TRADE:
                # Buy Crypto with FIAT
                if self.from_detail.currency.is_fiat is True and self.to_detail.currency.is_fiat is False:
                    self._handle_buy_crypto_with_fiat_cost_basis()

                # Sell Crypto to FIAT
                elif self.from_detail.currency.is_fiat is False and self.to_detail.currency.is_fiat is True:
                    self._handle_to_sell_crypto_to_fiat_cost_basis()
                    only_hmo_used = self._handle_from_crypto_cost_basis()

                # Trade Crypto to Crypto
                elif self.from_detail.currency.is_fiat is False and self.to_detail.currency.is_fiat is False:
                    self._handle_to_trade_crypto_to_crypto_cost_basis()
                    only_hmo_used = self._handle_from_crypto_cost_basis()

            # Transfer / SWAP
            else:
                self._handle_transfer_or_swap_cost_basis()

        # Deposit
        elif self.from_detail is None and self.to_detail is not None:
            if self.to_detail.currency.is_fiat:
                self._handle_fiat_deposit_cost_basis()
            else:
                self._handle_deposit_cost_basis()

        # Withdrawal
        elif self.from_detail is not None and self.to_detail is None:
            if self.from_detail.currency.is_fiat:
                self._handle_fiat_withdrawal_cost_basis()
            else:
                self._handle_withdrawal_cost_basis()

        # Fees
        if self.fee_detail is not None:
            if self.to_detail is not None and self.to_detail.currency == self.fee_detail.currency:
                # Handle cases where fee deducted from the amount received.
                self.to_detail.save(update_fields=["cost_basis"])

            self._handle_fee_cost_basis()

            # If deemed acquisition cost (HMO) is used, the fee can not be deducted
            # refs. https://www.vero.fi/henkiloasiakkaat/omaisuus/sijoitukset/osakkeiden_myynt/
            # Set fee to zero only if all sold tokens used HMO. If any tokens don't use HMO, fee can be deducted
            self.fee_amount = self.fee_detail.total_value if not only_hmo_used else Decimal(0)
        else:
            self.fee_amount = Decimal(0)

        TransactionDetail.objects.bulk_update(self.get_all_details(), fields=["cost_basis"])
        self.save(update_fields=["gain", "fee_amount"])

    def get_all_details(self) -> Iterable[TransactionDetail]:
        if self.from_detail:
            yield self.from_detail
        if self.to_detail:
            yield self.to_detail
        if self.fee_detail:
            yield self.fee_detail

    @atomic()
    def add_detail(self, type: str, wallet: Wallet, currency: Currency, quantity: Decimal):
        assert type in ["from_detail", "to_detail", "fee_detail"]

        detail: TransactionDetail | None = getattr(self, type, None)
        if detail is not None:  # Update
            detail.wallet = wallet
            detail.currency = currency
            detail.quantity = quantity
            detail.save()
        else:  # Create
            detail = TransactionDetail.objects.create(wallet=wallet, currency=currency, quantity=quantity)
            setattr(self, type, detail)
            self.save()


class TransactionDetailQuerySet(models.QuerySet):
    def order_by_timestamp(self):
        return self.annotate(
            tx_timestamp=Coalesce(F("from_detail__timestamp"), F("to_detail__timestamp"), F("fee_detail__timestamp"))
        ).order_by("tx_timestamp", "pk")

    def get_balances_for_snapshot(self, timestamp_from: date, timestamp_to: date) -> list[dict[str, Any]]:
        from crypto_fifo_taxes.models import SnapshotBalance

        # Last snapshot before this transaction
        snapshot_balance_qs = (
            SnapshotBalance.objects.only("currency_id", "tx_timestamp_date", "snapshot")
            .filter(
                currency_id=OuterRef("currency_id"),
                snapshot__date__lt=OuterRef("tx_timestamp_date"),
            )
            .order_by("-snapshot__date")
        )

        return (
            self.filter(
                tx_timestamp__gte=timestamp_from,
                tx_timestamp__lte=timestamp_to,
            )
            .alias(
                tx_timestamp_date=Cast("tx_timestamp", DateField()),
                # Currency coming in
                deposits=SQSum(
                    self.only("currency_id", "to_detail", "quantity").filter(
                        currency_id=OuterRef("currency_id"), to_detail__isnull=False
                    ),
                    sum_field="quantity",
                ),
                # Currency going out
                withdrawals=SQSum(
                    self.only("currency_id", "from_detail", "fee_detail", "quantity")
                    .filter(currency_id=OuterRef("currency_id"))
                    .filter(
                        Q(from_detail__isnull=False)
                        # Is fee and not a withdrawal to a third party (fee is included in from_detail amount)
                        | Q(fee_detail__isnull=False) & ~Q(fee_detail__transaction_type=TransactionType.WITHDRAW)
                    ),
                    sum_field="quantity",
                ),
                # Difference between deposits and withdrawals
                delta=ExpressionWrapper(
                    CoalesceZero(F("deposits")) - CoalesceZero(F("withdrawals")), output_field=DecimalField()
                ),
                # Avg cost basis if deposits
                avg_cost_basis=CoalesceZero(
                    SQAvg(
                        self.only("currency_id", "to_detail", "cost_basis").filter(
                            currency_id=OuterRef("currency_id"), to_detail__isnull=False
                        ),
                        avg_field="cost_basis",
                    )
                ),
                last_balance=CoalesceZero(Subquery(snapshot_balance_qs.values_list("quantity")[:1])),
                last_cost_basis=CoalesceZero(Subquery(snapshot_balance_qs.values_list("cost_basis")[:1])),
            )
            .annotate(
                new_balance=ExpressionWrapper(
                    CoalesceZero(F("last_balance")) + F("delta"), output_field=DecimalField()
                ),
                new_cost_basis=Case(
                    # Balance emptied or no last known cost basis
                    When(Q(new_balance=0) | Q(last_cost_basis=0), then=F("avg_cost_basis")),
                    # Negative delta, cost basis should not be changed from the last known value
                    When(delta__lt=0, then=F("last_cost_basis")),
                    # Calculate new cost basis weighted by quantity
                    default=ExpressionWrapper(
                        (F("last_balance") * F("last_cost_basis") + F("delta") * F("avg_cost_basis"))
                        / F("new_balance"),
                        output_field=DecimalField(),
                    ),
                    output_field=DecimalField(),
                ),
            )
            # Group by currency
            .order_by("currency_id")
            .distinct("currency_id")
            .values("currency_id", "new_balance", "new_cost_basis")
        )


class TransactionDetailManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related("from_detail", "to_detail", "fee_detail")


class TransactionDetail(models.Model):
    """
    Holds the answer the questions:
    What currency? Where did it come from/go to? How much of it? What was its cost basis?
    """

    wallet = models.ForeignKey(to="Wallet", on_delete=models.CASCADE, related_name="transaction_details")
    currency = models.ForeignKey(to="Currency", on_delete=models.PROTECT, related_name="transaction_details")
    quantity = TransactionDecimalField()
    cost_basis = TransactionDecimalField(null=True)  # Price for one cryptocurrency in FIAT

    objects = TransactionDetailManager.from_queryset(TransactionDetailQuerySet)()

    currency_id: int  # Type hint as int instead of Type[int]

    def __str__(self):
        return f"{self.currency.symbol} ({str(self.quantity).rstrip('0').rstrip('.')})"

    def __repr__(self):
        detail_type = self.transaction.transaction_type.label if self.transaction is not None else "UNKNOWN-TYPE"
        return f"<{self.__class__.__name__} ({self.id}): {detail_type} '{self.currency}' ({self.quantity})>"

    @property
    def transaction(self) -> Transaction | None:
        if hasattr(self, "from_detail"):
            return self.from_detail
        elif hasattr(self, "to_detail"):
            return self.to_detail
        elif hasattr(self, "fee_detail"):
            return self.fee_detail
        return None

    def get_consumable_balances(self) -> TransactionDetailQuerySet:
        return self.wallet.get_consumable_currency_balances(
            currency=self.currency,
            timestamp=self.transaction.timestamp,
            quantity=self.quantity,
        )

    def get_last_consumable_balance(self) -> TransactionDetail | None:
        """Get the balance of this currency after this transaction has been processed."""
        timestamp = self.transaction.timestamp
        # Include self in the query by adding 1 microsecond to the timestamp
        timestamp += datetime.timedelta(microseconds=1)

        last_balance_only = self.wallet.get_consumable_currency_balances(
            self.currency, quantity=None, timestamp=timestamp
        )

        if last_balance_only:
            return last_balance_only.last()
        return None

    @property
    def total_value(self) -> Decimal | None:
        if self.cost_basis is None:
            return None
        return self.cost_basis * self.quantity
