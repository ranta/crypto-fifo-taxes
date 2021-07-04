from django.db import models
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

    def _handle_buy_crypto_with_fiat_cost_basis(self):
        self.from_detail.cost_basis = self.from_detail.quantity

        # Simply distribute FIAT spent to crypto bought
        self.to_detail.cost_basis = self.from_detail.quantity / self.to_detail.quantity

    def _handle_sell_crypto_to_fiat_cost_basis(self):
        # TODO: Use FIFO to find exactly which coins were used
        self.from_detail.cost_basis = None

        # Use sold price as cost basis
        self.to_detail.cost_basis = self.to_detail.quantity / self.from_detail.quantity

    def fill_cost_basis(self):
        # TODO: Use `deemed acquisition cost` (hankintameno-olettama) when applicable
        # Buy Crypto with FIAT
        if self.from_detail.currency.is_fiat is True and self.to_detail.currency.is_fiat is False:
            self._handle_buy_crypto_with_fiat_cost_basis()

        # Sell Crypto to FIAT
        if self.from_detail.currency.is_fiat is False and self.to_detail.currency.is_fiat is True:
            self._handle_sell_crypto_to_fiat_cost_basis()


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
