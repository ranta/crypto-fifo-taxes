from decimal import Decimal

from django import template

from crypto_fifo_taxes.models import Transaction

register = template.Library()


@register.filter
def round_normalize(value: Decimal, precision: int) -> Decimal:
    return round(value, precision).normalize()


@register.filter
def get_spending_cost_basis(transaction: Transaction) -> Decimal:
    return transaction.from_detail.currency.get_fiat_price(
        transaction.timestamp, transaction.from_detail.wallet.fiat
    ).price
