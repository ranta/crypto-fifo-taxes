import datetime
from typing import Union

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
    # Unique string identifier for currency. Used for coingecko API
    cg_id = models.CharField(
        max_length=64,
        null=True,
        blank=True,
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

    def __str__(self):
        return f"{self.name} ({self.symbol})"

    def __repr__(self):
        return f"<{self.__class__.__name__} ({self.pk}): {self.name} [{'FIAT' if self.is_fiat else 'NON-FIAT'}]>"

    def get_fiat_price(self, date: Union[datetime.date, datetime.datetime], fiat: "Currency" = None) -> "CurrencyPrice":
        """
        Get the FIAT price for a crypto on a specific date.

        If no `fiat` currency is defined, settings.DEFAULT_FIAT_SYMBOL will be used instead.
        Fetch price for the crypto if no record for entered fiat and date is found.
        """
        if date is None:
            raise TypeError("Date must be entered!")

        if isinstance(date, datetime.datetime):
            date = date.date()

        if self.is_fiat is True:
            raise TypeError("Getting a FIAT currency's price in another FIAT currency is not supported yet.")

        currency_price = None
        # Get crypto price in entered FIAT currency
        if fiat is not None:
            assert isinstance(fiat, Currency) and fiat.is_fiat is True
            currency_price = self.prices.filter(date=date, fiat=fiat).first()

        # Price was not found for entered FIAT
        if currency_price is None:
            from crypto_fifo_taxes.utils.currency import fetch_currency_price

            fetch_currency_price(self, date)
            currency_price = self.prices.filter(date=date, fiat=fiat).first()

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

    def __str__(self):
        return f"{self.symbol}"

    def __repr__(self):
        return f"<{self.__class__.__name__} ({self.pk}): {self.symbol}>"


class CurrencyPrice(models.Model):
    """
    Crypto price in FIAT on a specific date.
    Tracking the price of a currency on day-scale is accurate enough.
    """

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
        # Only one crypto price per day per FIAT currency
        unique_together = (
            "currency",
            "date",
            "fiat",
        )

    def __str__(self):
        return f"{self.currency.symbol}'s  price in {self.fiat.symbol} on {self.date} ({self.price})"

    def __repr__(self):
        return (
            f"<{self.__class__.__name__} ({self.pk}): "
            f"FIAT: {self.fiat.symbol}, CRYPTO: {self.currency.symbol} ({self.date})>"
        )
