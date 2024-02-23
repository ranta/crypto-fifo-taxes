import pytest
from django.utils import timezone

from crypto_fifo_taxes.enums import TransactionLabel
from crypto_fifo_taxes.utils.transaction_creator import TransactionCreator
from crypto_fifo_taxes_tests.factories import CryptoCurrencyFactory, WalletFactory


@pytest.mark.django_db()
def test_mark_income_as_mining():
    wallet = WalletFactory.create()
    btc = CryptoCurrencyFactory.create(symbol="BTC")
    eth = CryptoCurrencyFactory.create(symbol="ETH")

    eth_tx = TransactionCreator(
        timestamp=timezone.now(),
        description="Mining Deposit",
        tx_id="0xf4c268755327817d449e852d9b5c9bb5a840f8080bf7328578c71b76e1a330a3",  # from Ethermine
    ).create_deposit(wallet=wallet, currency=eth, quantity=1)
    assert eth_tx.transaction_label == TransactionLabel.MINING

    btc_tx = TransactionCreator(
        timestamp=timezone.now(),
        description="Deposit",
        tx_id="4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b",
    ).create_deposit(wallet=wallet, currency=btc, quantity=1)
    assert btc_tx.transaction_label != TransactionLabel.MINING
