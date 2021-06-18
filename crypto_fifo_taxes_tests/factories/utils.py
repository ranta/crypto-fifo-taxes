from crypto_fifo_taxes_tests.factories import TransactionDetailFactory, TransactionFactory


class WalletHelper:
    """
    Simple utility, to allow creating simple deposits and withdrawals easily
    """

    def __init__(self, wallet):
        self.wallet = wallet

    def deposit(self, currency, quantity, **kwargs):
        TransactionFactory.create(
            to_detail=TransactionDetailFactory.create(wallet=self.wallet, currency=currency, quantity=quantity),
            **kwargs,
        )

    def withdraw(self, currency, quantity, **kwargs):
        TransactionFactory.create(
            from_detail=TransactionDetailFactory.create(wallet=self.wallet, currency=currency, quantity=quantity),
            **kwargs,
        )
