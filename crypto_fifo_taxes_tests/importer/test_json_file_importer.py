import os
from decimal import Decimal

import pytest
from django.conf import settings
from django.core.management import call_command

from crypto_fifo_taxes_tests.factories import WalletFactory


@pytest.mark.django_db
def test_binance_deposit_import():
    wallet_binance = WalletFactory.create(name="Binance")
    wallet_coinbase = WalletFactory.create(name="Coinbase")

    filepath = os.path.join(settings.BASE_DIR, "app", "import.json.template")
    call_command("import_json", file=filepath)

    assert wallet_binance.get_current_balance("BETH") == 1
    assert wallet_binance.get_current_balance("ETH") == -1
    assert wallet_binance.get_current_balance("BTC") == -1
    assert wallet_coinbase.get_current_balance("BTC") == Decimal("0.995")
