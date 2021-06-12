from datetime import datetime

from django.db import models
from django.utils.translation import gettext as _

from crypto_fifo_taxes.utils.models import TransactionDecimalField


class Currency(models.Model):
    """
    Basic information about a currency.
    e.g. `BTC`
    """

    symbol = models.CharField(
        max_length=30,
        verbose_name=_("Symbol"),
        unique=True,
    )
    name = models.CharField(
        max_length=30,
        verbose_name=_("Name"),
        unique=True,
    )
    icon = models.ImageField(
        upload_to="coin_icons",
        verbose_name=_("Icon"),
        blank=True,
        null=True,
    )
    is_fiat = models.BooleanField(
        default=False,
        verbose_name=_("Is FIAT"),
    )

    def get_fiat_price(self, date=None, fiat=None) -> "CurrencyPrice":
        """
        Get the FIAT price for a crypto on a specific date.

        If no `fiat` currency is defined, settings.DEFAULT_FIAT_CURRENCY will be used instead.
        Fetch price for the crypto if no record for entered fiat and date is found.
        """
        if date is None:
            raise TypeError("Date must be entered!")

        if isinstance(date, datetime):
            date = date.date()

        if self.is_fiat is False:
            raise TypeError("")

        currency_price = None
        # Get crypto price in entered FIAT currency
        if fiat is not None:
            assert isinstance(fiat, Currency) and fiat.is_fiat is True
            currency_price = self.prices.filter(date=date, fiat=fiat).first()

        # Price was not found for entered FIAT
        if currency_price is None:
            from crypto_fifo_taxes.utils.currency import get_default_fiat

            fiat = get_default_fiat()
            currency_price = self.prices.filter(date=date, fiat=fiat).first()
            if fiat is not None:
                pass  # TODO: Create price for missed FIAT by converting from default currency

        # Price was not found even in default currency
        if currency_price is None:
            pass  # TODO: Fetch coin price from an API

        return currency_price


class CurrencyPair(models.Model):
    """
    A trading pair between two currencies
    First symbol is the currency being bought, second is the currency used to buy.
    e.g. the pair `BTCUSDT`. BTC is bought using USDT
    """

    symbol = models.CharField(
        max_length=30,
        unique=True,
    )
    buy = models.ForeignKey(
        to=Currency,
        on_delete=models.PROTECT,
        related_name="buy_pairs",
    )
    sell = models.ForeignKey(
        to=Currency,
        on_delete=models.PROTECT,
        related_name="sell_pairs",
    )

    class Meta:
        unique_together = (
            "buy",
            "sell",
        )


class CurrencyPrice(models.Model):
    """Crypto price in FIAT on a specific date"""

    currency = models.ForeignKey(
        to=Currency,
        on_delete=models.CASCADE,
        related_name="prices",
        verbose_name=_("Currency"),
    )
    fiat = models.ForeignKey(
        to=Currency,
        on_delete=models.CASCADE,
        related_name="+",
        verbose_name=_("FIAT"),
    )
    date = models.DateField()
    price = TransactionDecimalField()
    market_cap = TransactionDecimalField()
    volume = TransactionDecimalField()

    class Meta:
        # A price can only have one price per day per FIAT currency
        unique_together = (
            "currency",
            "date",
            "fiat",
        )
