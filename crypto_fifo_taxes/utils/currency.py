from functools import lru_cache

from django.conf import settings

from crypto_fifo_taxes.models import Currency


@lru_cache()
def get_default_fiat() -> Currency:
    """Return the currency object for default fiat currency"""
    return Currency.objects.get(is_fiat=True, symbol=settings.DEFAULT_FIAT_CURRENCY)
