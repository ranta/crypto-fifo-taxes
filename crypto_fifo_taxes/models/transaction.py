from decimal import Decimal

from django.db import models
from django.db.transaction import atomic
from enumfields import EnumField

from crypto_fifo_taxes.enums import TransactionLabel, TransactionType
from crypto_fifo_taxes.utils.models import TransactionDecimalField


class Transaction(models.Model):
    """Contains static values for a transaction"""

    timestamp = models.DateTimeField()
    transaction_type = EnumField(TransactionType)
    transaction_label = EnumField(TransactionLabel, default=TransactionLabel.UNKNOWN)
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

    def __str__(self):
        if self.transaction_type == TransactionType.DEPOSIT:
            detail_str = str(self.to_detail)
        elif self.transaction_type == TransactionType.WITHDRAW:
            detail_str = str(self.from_detail)
        else:
            detail_str = f"{self.from_detail} to {self.to_detail}"
        return f"{self.transaction_type.label} of {detail_str}"

    def __repr__(self):
        return f"<{self.__class__.__name__} ({self.id}): {str(self)}>"

    def _get_from_detail_cost_basis(self) -> Decimal:
        """
        Use FIFO to get used currency quantities and cost bases.
        Then average them and return the result
        """
        consumable_balances = self.from_detail.get_consumable_balances()
        required_quantity = self.from_detail.quantity
        cost_bases: list[tuple] = []  # [(quantity, cost_basis)]

        for balance in consumable_balances:
            if required_quantity == Decimal(0):
                # Nothing left to do
                break

            if required_quantity >= balance.quantity:
                # Fully consume deposit balance
                cost_bases.append((balance.quantity, balance.cost_basis))
                required_quantity -= balance.quantity
            else:
                # Consume only the required quantity
                cost_bases.append((required_quantity, balance.cost_basis))
                required_quantity -= required_quantity

        if required_quantity > Decimal(0):
            raise ValueError("Transaction from detail quantity is more than wallet has available to consume!")

        sum_quantity = sum(i for i, _ in cost_bases)
        total_value = sum(i * j for i, j in cost_bases)
        cost_basis = total_value / sum_quantity
        return cost_basis

    def _handle_buy_crypto_with_fiat_cost_basis(self):
        # from_detail cost_basis is simply the amount of FIAT it was bought with
        self.from_detail.cost_basis = self.from_detail.quantity
        self.from_detail.save()

        # Distribute amount of FIAT spent equally to crypto bought
        self.to_detail.cost_basis = self.from_detail.quantity / self.to_detail.quantity
        self.to_detail.save()

    def _handle_sell_crypto_to_fiat_cost_basis(self):
        self.from_detail.cost_basis = self._get_from_detail_cost_basis()
        self.from_detail.save()

        # Use sold price as cost basis
        self.to_detail.cost_basis = self.to_detail.quantity / self.from_detail.quantity
        self.to_detail.save()

    @atomic()
    def fill_cost_basis(self):
        # TODO: Use `deemed acquisition cost` (hankintameno-olettama) when applicable
        # TODO: Reduce fee amount from cost-basis
        # TODO: Transfer funds to and from another wallet
        # TODO: Swap currency to another

        # Trade / Transfer / Swap
        if self.from_detail is not None and self.to_detail is not None:
            # Buy Crypto with FIAT
            if self.from_detail.currency.is_fiat is True and self.to_detail.currency.is_fiat is False:
                self._handle_buy_crypto_with_fiat_cost_basis()

            # Sell Crypto to FIAT
            elif self.from_detail.currency.is_fiat is False and self.to_detail.currency.is_fiat is True:
                self._handle_sell_crypto_to_fiat_cost_basis()

            # Trade Crypto to Crypto
            if self.from_detail.currency.is_fiat is False and self.to_detail.currency.is_fiat is False:
                pass  # TODO

        # Deposit
        if self.from_detail is None and self.to_detail is not None:
            pass  # TODO

        # Withdrawal
        if self.from_detail is not None and self.to_detail is None:
            pass  # TODO


class TransactionDetail(models.Model):
    wallet = models.ForeignKey(to="Wallet", on_delete=models.CASCADE, related_name="transaction_details")
    currency = models.ForeignKey(to="Currency", on_delete=models.PROTECT, related_name="+")
    quantity = TransactionDecimalField()
    cost_basis = TransactionDecimalField(null=True)  # Calculated field

    def __str__(self):
        return f"{self.currency.symbol} ({self.quantity})"

    def __repr__(self):
        if self.transaction is not None:
            detail_type = self.transaction.transaction_type.label
        else:
            detail_type = "UNKNOWN-TYPE"
        return f"<{self.__class__.__name__} ({self.id}): {detail_type} '{self.currency}' ({self.quantity})>"

    @property
    def transaction(self):
        if hasattr(self, "from_detail"):
            return self.from_detail
        elif hasattr(self, "to_detail"):
            return self.to_detail
        elif hasattr(self, "fee_detail"):
            return self.fee_detail
        return None

    def get_consumable_balances(self):
        return self.wallet.get_consumable_currency_balances(
            self.currency, quantity=self.quantity, timestamp=self.transaction.timestamp
        )
