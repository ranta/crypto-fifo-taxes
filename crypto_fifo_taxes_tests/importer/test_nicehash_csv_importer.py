import os
from decimal import Decimal

import pytest
from django.conf import settings
from django.core.management import call_command

from crypto_fifo_taxes_tests.factories import CryptoCurrencyFactory, WalletFactory


@pytest.mark.django_db
def test_json_import_management_command():
    wallet = WalletFactory.create(name="Nicehash")
    CryptoCurrencyFactory.create(symbol="BTC")

    filepath = os.path.join(settings.BASE_DIR, "nicehash_report.csv.template")
    call_command("import_nicehash", file=filepath)

    assert wallet.get_current_balance("BTC") == Decimal("0.00099000")
