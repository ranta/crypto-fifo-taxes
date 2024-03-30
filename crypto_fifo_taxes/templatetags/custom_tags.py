from decimal import Decimal

from django import template

from crypto_fifo_taxes.models import Transaction

register = template.Library()


@register.filter
def round_normalize(value: Decimal, precision: int) -> Decimal:
    """
    Rounds and normalizes a Decimal value.

    Example:
    {{ value|round_normalize:2 }}
    """
    if not value:
        return Decimal(0)

    return round(value, precision).normalize()


@register.filter
def get_spending_cost_basis(transaction: Transaction) -> Decimal:
    return transaction.from_detail.currency.get_fiat_price(transaction.timestamp).price
