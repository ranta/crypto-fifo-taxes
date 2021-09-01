from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional, Union

from django.db.transaction import atomic

from crypto_fifo_taxes.enums import TransactionLabel, TransactionType
from crypto_fifo_taxes.models import Currency, Transaction, TransactionDetail, Wallet


class TransactionCreator:
    """
    Utility to simplify creating transactions.

    When creating transactions always use a new instance of TransactionCreator for each transaction,
    to prevent data from the old transaction being passed through.

    Allows setting transaction details, then creating everything in one go.

    Example usages:
    Deposit:
    >>>TransactionCreator().create_deposit(timestamp=timezone.now(), wallet=wallet, currency=fiat, quantity=500)

    Trade:
    Requires manually adding transaction details e.g. with `add_from_detail` and `add_to_detail` to use
    >>>tx_creator = TransactionCreator()
    >>>tx_creator.add_from_detail(wallet=wallet, currency=fiat, quantity=Decimal(200))
    >>>tx_creator.add_to_detail(wallet=wallet, currency=crypto, quantity=Decimal(20))
    >>>tx_creator.add_fee_detail(wallet=wallet, currency=crypto, quantity=Decimal(0.01))
    >>>tx_creator.create_trade(timestamp=timezone.now())
    """

    def __init__(
        self,
        timestamp: Optional[datetime] = None,
        type=TransactionType.UNKNOWN,
        label=TransactionLabel.UNKNOWN,
        fill_cost_basis: bool = True,
        description: Optional[str] = "",
        tx_id: Optional[str] = "",
    ):
        self.timestamp: Optional[datetime] = timestamp
        self.transaction_type: TransactionType = type
        self.transaction_label: TransactionLabel = label
        self.description = description
        self.tx_id = tx_id

        self.from_detail: Optional[TransactionDetail] = None
        self.to_detail: Optional[TransactionDetail] = None
        self.fee_detail: Optional[TransactionDetail] = None

        self.fill_cost_basis: bool = fill_cost_basis

    def _add_detail(
        self,
        wallet: Wallet,
        currency: Currency,
        quantity: Union[Decimal, int],
        cost_basis: Optional[Decimal] = None,
        prefix: str = "",
    ):
        detail = TransactionDetail(wallet=wallet, currency=currency, quantity=quantity, cost_basis=cost_basis)
        setattr(self, f"{prefix}_detail", detail)

    def add_from_detail(
        self,
        wallet: Wallet,
        currency: Currency,
        quantity: Union[Decimal, int],
        cost_basis: Optional[Decimal] = None,
    ):
        self._add_detail(wallet, currency, quantity, cost_basis, prefix="from")

    def add_to_detail(
        self,
        wallet: Wallet,
        currency: Currency,
        quantity: Union[Decimal, int],
        cost_basis: Optional[Decimal] = None,
    ):
        self._add_detail(wallet, currency, quantity, cost_basis, prefix="to")

    def add_fee_detail(
        self,
        wallet: Wallet,
        currency: Currency,
        quantity: Union[Decimal, int],
        cost_basis: Optional[Decimal] = None,
    ):
        """
        The fee currency should always be the currency you receive unless paid a third currency e.g. BNB.
        e.g. in a ETH -> EUR trade, the fee currency would be EUR (or BNB)
        """
        self._add_detail(wallet, currency, quantity, cost_basis, prefix="fee")

    def get_details(self) -> Dict[str, TransactionDetail]:
        """Get all detail values that are not None"""
        all_details = {}
        for detail_field in ["from_detail", "to_detail", "fee_detail"]:
            detail = getattr(self, detail_field, None)
            if detail:
                all_details[detail_field] = detail
        return all_details

    def create_deposit(self, **kwargs):
        self.transaction_type = TransactionType.DEPOSIT
        self.timestamp = kwargs.pop("timestamp", self.timestamp)
        self.description = kwargs.pop("description", self.description)
        self.tx_id = kwargs.pop("tx_id", self.tx_id)

        # Accept to_details values in kwargs
        if len(kwargs):
            self.add_to_detail(**kwargs)
        return self.create_transaction()

    def create_withdrawal(self, **kwargs):
        self.transaction_type = TransactionType.WITHDRAW
        self.timestamp = kwargs.pop("timestamp", self.timestamp)
        self.description = kwargs.pop("description", self.description)
        self.tx_id = kwargs.pop("tx_id", self.tx_id)

        # Accept from_details values in kwargs
        if len(kwargs):
            self.add_from_detail(**kwargs)
        return self.create_transaction()

    def create_trade(self, **kwargs):
        self.transaction_type = TransactionType.TRADE
        return self.create_transaction(**kwargs)

    def create_transfer(self, **kwargs):
        self.transaction_type = TransactionType.TRANSFER
        return self.create_transaction(**kwargs)

    def create_swap(self, **kwargs):
        self.transaction_type = TransactionType.SWAP
        return self.create_transaction(**kwargs)

    def _validate_transaction_type(self):
        assert self.transaction_type is not None
        assert self.transaction_type != TransactionType.UNKNOWN

        # Validate correct details are entered for transaction type
        if self.transaction_type == TransactionType.DEPOSIT:
            assert self.from_detail is None and self.to_detail is not None
        elif self.transaction_type == TransactionType.WITHDRAW:
            assert self.from_detail is not None and self.to_detail is None
            if self.fee_detail:
                # Having a larger fee than amount sent makes no sense
                assert self.from_detail.quantity > self.fee_detail.quantity
        else:
            assert self.from_detail is not None and self.to_detail is not None

    @atomic()
    def create_transaction(self, **kwargs):
        kwargs.setdefault("timestamp", self.timestamp)
        kwargs.setdefault("description", self.description)
        kwargs.setdefault("tx_id", self.tx_id)
        assert kwargs["timestamp"] is not None

        self._validate_transaction_type()

        details = self.get_details()
        for key, detail in details.items():
            detail.save()

        transaction = Transaction(
            transaction_type=self.transaction_type,
            transaction_label=self.transaction_label,
            **details,
            **kwargs,
        )
        transaction.save()

        if self.fill_cost_basis:
            transaction.fill_cost_basis()
        return transaction
