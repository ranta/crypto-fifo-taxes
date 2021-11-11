from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def round_normalize(value: Decimal, precision: int) -> Decimal:
    return round(value, precision).normalize()
