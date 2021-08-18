from decimal import Decimal
from typing import List, Optional

from django.db import models
from django.db.transaction import atomic
from enumfields import EnumIntegerField

from crypto_fifo_taxes.enums import TransactionLabel, TransactionType
from crypto_fifo_taxes.utils.models import TransactionDecimalField


class Transaction(models.Model):
    """Contains static values for a transaction"""

    timestamp = models.DateTimeField()
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
    tx_id = models.CharField(max_length=256, blank=True, null=True)
    order_id = models.CharField(max_length=256, blank=True, null=True)

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

    @staticmethod
    def _get_detail_cost_basis(
        transaction_detail: "TransactionDetail", sell_price: Optional[Decimal] = None
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
        consumable_balances: List["TransactionDetail"] = transaction_detail.get_consumable_balances()
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

            assert balance.cost_basis, (
                f"TransactionDetail (id: {balance.id}, {balance}) is missing its `cost_basis`." f" Unable to continue"
            )
            if required_quantity >= balance.quantity_left:
                # Fully consume deposit balance
                cost_bases.append((balance.quantity_left, apply_hmo(balance.cost_basis)))
                required_quantity -= balance.quantity_left
            else:
                # Consume only the required quantity
                cost_bases.append((required_quantity, apply_hmo(balance.cost_basis)))
                required_quantity -= required_quantity

        if required_quantity > Decimal(0):
            raise ValueError(
                "Transaction from detail quantity is more than wallet has available to consume! "
                f"Required: {required_quantity} {transaction_detail.currency}"
            )

        sum_quantity = sum(i for i, _ in cost_bases)
        total_value = sum(i * j for i, j in cost_bases)
        cost_basis = total_value / sum_quantity
        return (Decimal(cost_basis), only_hmo_used)

    def _get_from_detail_cost_basis(self, sell_price: Optional[Decimal] = None) -> tuple[Decimal, bool]:
        return self._get_detail_cost_basis(transaction_detail=self.from_detail, sell_price=sell_price)

    def _get_fee_detail_cost_basis(self) -> Decimal:
        """TODO Use HMO for trade fees"""
        return self._get_detail_cost_basis(transaction_detail=self.fee_detail)[0]

    def _handle_buy_crypto_with_fiat_cost_basis(self) -> None:
        # from_detail cost_basis is simply the amount of FIAT it was bought with
        self.from_detail.cost_basis = Decimal(1)
        self.from_detail.save()

        # Distribute amount of FIAT spent equally to crypto bought
        self.to_detail.cost_basis = self.from_detail.quantity / self.to_detail.quantity
        self.to_detail.save()

    def _handle_to_sell_crypto_to_fiat_cost_basis(self) -> None:
        # Use sold price as cost basis
        self.to_detail.cost_basis = Decimal(1)
        self.to_detail.save()

    def _handle_to_trade_crypto_to_crypto_cost_basis(self) -> None:
        # Use sold price as cost basis
        currency_value = self.from_detail.currency.get_fiat_price(self.timestamp, self.from_detail.wallet.fiat).price
        self.to_detail.cost_basis = (self.from_detail.quantity * currency_value) / self.to_detail.quantity
        self.to_detail.save()

    def _handle_from_crypto_cost_basis(self) -> bool:
        # Sell value is divided for every sold token to find the average price
        sell_price = self.to_detail.total_value / self.from_detail.quantity
        from_cost_basis, only_hmo_used = self._get_from_detail_cost_basis(sell_price=sell_price)
        self.from_detail.cost_basis = from_cost_basis
        self.from_detail.save()

        self.gain = self.to_detail.total_value - self.from_detail.total_value
        self.save()

        return only_hmo_used

    def _handle_transfer_or_swap_cost_basis(self) -> None:
        """
        FIXME:
        If multiple different cost_basis is present on currencies in a transfer, this changes the cost_basis of the
        coins to the average of all transferred coins. The original cost_basis shouldn't be changed on SWAP or transfer.
        This shouldn't affect the end result, except in a few very rare cases.
        """
        cost_basis = self._get_from_detail_cost_basis()[0]

        self.from_detail.cost_basis = cost_basis
        self.from_detail.save()

        self.to_detail.cost_basis = cost_basis
        self.to_detail.save()

        self.gain = Decimal(0)
        self.save()

    def _handle_deposit_cost_basis(self) -> None:
        """
        If the funds came from `nowhere`, it 100% gains.
        Deposits can be from e.g. Staking or Mining.
        """
        if self.to_detail.currency.is_fiat:
            self.to_detail.cost_basis = Decimal(1)
            self.gain = Decimal(0)
        else:
            currency_value = self.to_detail.currency.get_fiat_price(self.timestamp, self.to_detail.wallet.fiat).price
            self.to_detail.cost_basis = currency_value
            self.gain = currency_value * self.to_detail.quantity

        self.to_detail.save()
        self.save()

    def _handle_withdrawal_cost_basis(self) -> None:
        """
        Funds are sent to some third party entity.
        e.g. Paying for goods and services directly with crypto
        This realizes any profits made from value appreciation
        """
        if self.from_detail.currency.is_fiat:
            self.from_detail.cost_basis = Decimal(1)
            self.gain = Decimal(0)
        else:
            sell_price = self.from_detail.currency.get_fiat_price(self.timestamp, self.from_detail.wallet.fiat).price
            from_cost_basis, only_hmo_used = self._get_from_detail_cost_basis(sell_price=sell_price)
            self.from_detail.cost_basis = from_cost_basis
            self.gain = (sell_price - from_cost_basis) * self.from_detail.quantity

        self.from_detail.save()
        self.save()

    def _handle_fee_cost_basis(self) -> None:
        cost_basis = self._get_fee_detail_cost_basis()
        self.fee_detail.cost_basis = cost_basis
        self.fee_detail.save()

    @atomic()
    def fill_cost_basis(self) -> None:
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
        if self.from_detail is None and self.to_detail is not None:
            self._handle_deposit_cost_basis()

        # Withdrawal
        if self.from_detail is not None and self.to_detail is None:
            self._handle_withdrawal_cost_basis()

        # Fees
        if self.fee_detail is not None:
            self._handle_fee_cost_basis()

            # If deemed acquisition cost (HMO) is used, the fee can not be deducted
            # refs. https://www.vero.fi/henkiloasiakkaat/omaisuus/sijoitukset/osakkeiden_myynt/
            # Set fee to zero only if all sold tokens used HMO. If any tokens don't use HMO, fee can be deducted
            self.fee_amount = self.fee_detail.total_value if not only_hmo_used else Decimal(0)
            self.save()


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
    def transaction(self) -> Optional["Transaction"]:
        if hasattr(self, "from_detail"):
            return self.from_detail
        elif hasattr(self, "to_detail"):
            return self.to_detail
        elif hasattr(self, "fee_detail"):
            return self.fee_detail
        return None

    def get_consumable_balances(self) -> List["TransactionDetail"]:
        return self.wallet.get_consumable_currency_balances(
            self.currency, quantity=self.quantity, timestamp=self.transaction.timestamp
        )

    @property
    def total_value(self) -> Decimal:
        return self.cost_basis * self.quantity
