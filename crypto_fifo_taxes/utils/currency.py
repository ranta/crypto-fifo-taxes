from functools import lru_cache
from typing import Union

from django.conf import settings

from crypto_fifo_taxes.models import Currency


@lru_cache()
def get_default_fiat() -> Currency:
    """Return the currency object for default fiat currency"""
    return Currency.objects.get(is_fiat=True, symbol=settings.DEFAULT_FIAT_CURRENCY)


@lru_cache()
def get_currency(currency: Union[Currency, str, int]) -> Currency:
    if type(currency) == str:
        return Currency.objects.get(symbol=currency)
    if type(currency) == int:
        return Currency.objects.get(id=currency)
    return currency
