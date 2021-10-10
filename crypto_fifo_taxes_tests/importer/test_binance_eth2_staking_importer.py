import os
from decimal import Decimal

import pytest
from django.conf import settings
from django.core.management import call_command

from crypto_fifo_taxes.models import Transaction
from crypto_fifo_taxes_tests.factories import WalletFactory


@pytest.mark.django_db
def test_binance_eth2_staking_importer_management_command():
    wallet_binance = WalletFactory.create(name="Binance")

    filepath = os.path.join(settings.BASE_DIR, "binance_eth2_staking.json.template")
    call_command("import_binance_eth2_json", file=filepath)

    assert Transaction.objects.all().count() == 2
    assert wallet_binance.get_current_balance("BETH") == Decimal("0.00250000") + Decimal("0.00300000")
