import pytest

from crypto_fifo_taxes.utils.currency import get_currency
from crypto_fifo_taxes_tests.factories import CryptoCurrencyFactory


@pytest.mark.django_db()
def test__get_currency__legacy_symbol_from_new(settings):
    settings.RENAMED_SYMBOLS = {"NEW": "OLD"}

    currency = CryptoCurrencyFactory.create(symbol="OLD")

    assert get_currency("NEW") == currency


@pytest.mark.django_db()
def test__get_currency__new_symbol_from_legacy(settings):
    settings.RENAMED_SYMBOLS = {"NEW": "OLD"}

    currency = CryptoCurrencyFactory.create(symbol="NEW")

    assert get_currency("OLD") == currency
