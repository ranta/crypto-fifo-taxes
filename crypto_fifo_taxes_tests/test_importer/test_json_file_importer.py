import os
from decimal import Decimal

import pytest
from django.conf import settings
from django.core.management import call_command

from crypto_fifo_taxes_tests.factories import TransactionFactory, WalletFactory


@pytest.mark.django_db()
def test_json_import_management_command():
    wallet_binance = WalletFactory.create(name="Binance")
    wallet_coinbase = WalletFactory.create(name="Coinbase")
    wallet_cold = WalletFactory.create(name="Cold Wallet")

    TransactionFactory.create(
        tx_id="1234dbbd89333347002d73sss8026feb5f6ggggg81734bad136d18a44df91234"  # from template import.json.template
    )

    filepath = os.path.join(settings.BASE_DIR, "import.json.template")
    call_command("import_json", file=filepath)

    assert wallet_binance.get_current_balance("BETH") == 1
    assert wallet_binance.get_current_balance("ETH") == -1
    assert wallet_binance.get_current_balance("BTC") == -1
    assert wallet_coinbase.get_current_balance("BTC") == Decimal("0.995")
    assert wallet_cold.get_current_balance("BTC") == Decimal("0.995")
