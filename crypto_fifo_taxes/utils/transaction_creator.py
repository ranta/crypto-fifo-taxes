from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional, Union

from django.db.transaction import atomic

from crypto_fifo_taxes.enums import TransactionType
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
    >>>tx_creator.create_trade(timestamp=timezone.now())
    """

    def __init__(self):
        self.timestamp = None
        self.transaction_type = None
        self.transaction_label = None
        self.description = None

        self.from_detail = None
        self.to_detail = None
        self.fee_detail = None

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
        self._add_detail(wallet, currency, quantity, cost_basis, prefix="fee")

    def get_details(self) -> Dict[str, TransactionDetail]:
        """Get all detail values that are not None"""
        all_details = {}
        for detail_field in ["from_detail", "to_detail", "fee_detail"]:
            detail = getattr(self, detail_field, None)
            if detail:
                all_details[detail_field] = detail
        return all_details

    def create_deposit(self, timestamp: datetime, description: str = "", **kwargs):
        self.transaction_type = TransactionType.DEPOSIT
        # Accept to_details values in kwargs
        if len(kwargs):
            self.add_to_detail(**kwargs)
        return self._create_transaction(timestamp, description)

    def create_withdrawal(self, timestamp: datetime, description: str = "", **kwargs):
        self.transaction_type = TransactionType.WITHDRAW
        # Accept from_details values in kwargs
        if len(kwargs):
            self.add_from_detail(**kwargs)
        return self._create_transaction(timestamp, description)

    def create_trade(self, timestamp: datetime, description: str = ""):
        self.transaction_type = TransactionType.TRADE
        return self._create_transaction(timestamp, description)

    def create_transfer(self, timestamp: datetime, description: str = ""):
        self.transaction_type = TransactionType.TRANSFER
        return self._create_transaction(timestamp, description)

    def create_swap(self, timestamp: datetime, description: str = ""):
        self.transaction_type = TransactionType.SWAP
        return self._create_transaction(timestamp, description)

    @atomic()
    def _create_transaction(self, timestamp: datetime, description: str = "", **kwargs):
        assert self.transaction_type is not None
        # Validate correct details are entered for transaction type
        if self.transaction_type == TransactionType.DEPOSIT:
            assert self.from_detail is None and self.to_detail is not None
        elif self.transaction_type == TransactionType.WITHDRAW:
            assert self.from_detail is not None and self.to_detail is None
        else:
            assert self.from_detail is not None and self.to_detail is not None

        details = self.get_details()
        for key, detail in details.items():
            detail.save()

        transaction = Transaction(
            timestamp=timestamp, description=description, transaction_type=self.transaction_type, **details, **kwargs
        )
        transaction.save()
        transaction.fill_cost_basis()
        return transaction
