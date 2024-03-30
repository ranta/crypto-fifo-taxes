import pytest

from crypto_fifo_taxes.utils.currency import (
    get_currency,
    get_fiat_currency,
    get_or_create_currency,
    get_or_create_currency_pair,
)


@pytest.fixture(autouse=True)
def _clear_cache_between_tests():
    """Clear the caches or functions that's cache will impact tests"""
    get_fiat_currency.cache_clear()
    get_currency.cache_clear()
    get_or_create_currency.cache_clear()
    get_or_create_currency_pair.cache_clear()
