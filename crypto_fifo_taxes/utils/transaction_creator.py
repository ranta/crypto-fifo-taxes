import logging
from datetime import datetime
from decimal import Decimal

from django.db.transaction import atomic

from crypto_fifo_taxes.enums import TransactionLabel, TransactionType
from crypto_fifo_taxes.models import Currency, Snapshot, Transaction, TransactionDetail, Wallet
from crypto_fifo_taxes.utils.ethplorer import get_ethplorer_client

logger = logging.getLogger(__name__)

class TransactionCreator:
    """
    Utility to simplify creating transactions.

    When creating transactions always use a new instance of TransactionCreator for each transaction,
    to prevent data from the old transaction being passed through.

    Allows setting transaction details, then creating everything in one go.

    Example usages:
    Deposit:
    >>>TransactionCreator(timestamp=timezone.now()).create_deposit(wallet=wallet, currency=fiat, quantity=500)

    Trade:
    Requires manually adding transaction details e.g. with `add_from_detail` and `add_to_detail` to use
    >>>tx_creator = TransactionCreator(timestamp=timezone.now())
    >>>tx_creator.add_from_detail(wallet=wallet, currency=fiat, quantity=Decimal(200))
    >>>tx_creator.add_to_detail(wallet=wallet, currency=crypto, quantity=Decimal(20))
    >>>tx_creator.add_fee_detail(wallet=wallet, currency=crypto, quantity=Decimal(0.01))
    >>>tx_creator.create_trade()
    """

    def __init__(
        self,
        timestamp: datetime | None = None,
        description: str | None = "",
        tx_id: str | None = "",
        type=TransactionType.UNKNOWN,
        label=TransactionLabel.UNKNOWN,
        fill_cost_basis: bool = True,
    ):
        self.timestamp: datetime | None = timestamp
        self.description: str = description
        self.tx_id: str = tx_id
        self.transaction_type: TransactionType = type
        self.transaction_label: TransactionLabel = label

        self.from_detail: TransactionDetail | None = None
        self.to_detail: TransactionDetail | None = None
        self.fee_detail: TransactionDetail | None = None

        self.fill_cost_basis: bool = fill_cost_basis

    def _add_detail(
        self,
        wallet: Wallet,
        currency: Currency,
        quantity: Decimal | int,
        cost_basis: Decimal | None = None,
        prefix: str = "",
    ) -> None:
        if quantity == 0:
            # TODO: Logging
            logger.warning(f"WARN: Tried to add zero value {prefix} detail with currency{currency}.")
            return

        detail = TransactionDetail(wallet=wallet, currency=currency, quantity=quantity, cost_basis=cost_basis)
        setattr(self, f"{prefix}_detail", detail)

    def add_from_detail(
        self,
        wallet: Wallet,
        currency: Currency,
        quantity: Decimal | int,
        cost_basis: Decimal | None = None,
    ) -> None:
        self._add_detail(wallet, currency, quantity, cost_basis, prefix="from")

    def add_to_detail(
        self,
        wallet: Wallet,
        currency: Currency,
        quantity: Decimal | int,
        cost_basis: Decimal | None = None,
    ) -> None:
        self._add_detail(wallet, currency, quantity, cost_basis, prefix="to")

    def add_fee_detail(
        self,
        wallet: Wallet,
        currency: Currency,
        quantity: Decimal | int,
        cost_basis: Decimal | None = None,
    ) -> None:
        """
        The fee currency should always be the currency you receive unless paid a third currency e.g. BNB.
        e.g. in a ETH -> EUR trade, the fee currency would be EUR (or BNB)
        """
        self._add_detail(wallet, currency, quantity, cost_basis, prefix="fee")

    def _get_details(self) -> dict[str, TransactionDetail]:
        """Get all detail values that are not None"""
        all_details = {}
        for detail_field in ["from_detail", "to_detail", "fee_detail"]:
            detail = getattr(self, detail_field, None)
            if detail:
                all_details[detail_field] = detail
        return all_details

    def create_deposit(self, **kwargs) -> Transaction:
        self.transaction_type = TransactionType.DEPOSIT

        # Accept to_details values in kwargs
        if len(kwargs):
            self.add_to_detail(**kwargs)
        return self.create_transaction()

    def create_withdrawal(self, **kwargs) -> Transaction:
        self.transaction_type = TransactionType.WITHDRAW

        # Accept from_details values in kwargs
        if len(kwargs):
            self.add_from_detail(**kwargs)
        return self.create_transaction()

    def create_trade(self) -> Transaction:
        self.transaction_type = TransactionType.TRADE
        return self.create_transaction()

    def create_transfer(self) -> Transaction:
        self.transaction_type = TransactionType.TRANSFER
        return self.create_transaction()

    def create_swap(self) -> Transaction:
        self.transaction_type = TransactionType.SWAP
        return self.create_transaction()

    def _validate_transaction_type(self) -> None:
        assert self.transaction_type is not None
        assert self.transaction_type != TransactionType.UNKNOWN

        # Validate correct details are entered for transaction type
        if self.transaction_type == TransactionType.DEPOSIT:
            assert self.from_detail is None
            assert self.to_detail is not None
        elif self.transaction_type == TransactionType.WITHDRAW:
            assert self.from_detail is not None
            assert self.to_detail is None
            if self.fee_detail:
                # Having a larger fee than amount sent makes no sense
                assert self.from_detail.quantity > self.fee_detail.quantity
        else:
            assert self.from_detail is not None
            assert self.to_detail is not None

    def _set_mining_label(self) -> None:
        """Set mining label for ETH deposits that originate from mining pools."""
        if self.tx_id and self.transaction_type == TransactionType.DEPOSIT and self.to_detail.currency.symbol == "ETH":
            client = get_ethplorer_client()
            is_mining = client.is_tx_from_mining_pool(self.tx_id)
            if is_mining:
                self.transaction_label = TransactionLabel.MINING

    @atomic()
    def create_transaction(self) -> Transaction:
        assert self.timestamp is not None

        self._validate_transaction_type()
        self._set_mining_label()

        details = self._get_details()
        for _key, detail in details.items():
            detail.save()

        transaction = Transaction(
            timestamp=self.timestamp,
            description=self.description,
            tx_id=self.tx_id,
            transaction_type=self.transaction_type,
            transaction_label=self.transaction_label,
            **details,
        )
        transaction.save()

        if self.fill_cost_basis:
            transaction.fill_cost_basis()

        Snapshot.objects.filter(date__gte=self.timestamp.date()).delete()

        return transaction
