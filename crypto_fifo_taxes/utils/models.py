from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class TransactionDecimalField(models.DecimalField):
    def __init__(
        self,
        verbose_name=None,
        name=None,
        default=Decimal(0),
        max_digits=32,
        decimal_places=14,
        validators=None,
        **kwargs
    ):
        if validators is None:
            validators = [MinValueValidator(Decimal("0"))]

        super().__init__(
            verbose_name,
            name,
            default=default,
            validators=validators,
            max_digits=max_digits,
            decimal_places=decimal_places,
            **kwargs
        )
