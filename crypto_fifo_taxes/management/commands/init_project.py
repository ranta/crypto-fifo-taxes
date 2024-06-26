import logging
import os
import sys

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import BaseCommand

from crypto_fifo_taxes.models import Currency, Wallet

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)


def _create_initial_currencies() -> None:
    # Create required FIAT currencies
    Currency.objects.update_or_create(
        symbol=settings.DEFAULT_FIAT_SYMBOL,
        defaults={
            "name": settings.DEFAULT_FIAT_CURRENCY["name"],
            "cg_id": settings.DEFAULT_FIAT_CURRENCY["cg_id"],
            "is_fiat": True,
        },
    )

    # Create all predefined currencies
    for symbol, data in settings.COINGECKO_MAPPED_CRYPTO_CURRENCIES.items():
        Currency.objects.update_or_create(
            symbol=symbol,
            defaults={
                "name": data["name"],
                "cg_id": data["cg_id"],
                "is_fiat": False,
            },
        )


def _create_admin_user() -> User:
    # Create admin user
    admin_user, admin_created = User.objects.get_or_create(
        username="admin",
        defaults={
            "email": "admin@example.com",
            "first_name": "Admin",
            "last_name": "Superuser",
            "is_staff": True,
            "is_active": True,
            "is_superuser": True,
        },
    )
    if admin_created:
        admin_user.set_password("admin")
        admin_user.save()
    return admin_user


def _create_initial_wallets() -> None:
    wallet_names = [w.strip() for w in os.environ.get("WALLET_NAMES").split(",")]
    for wallet_name in wallet_names:
        Wallet.objects.get_or_create(name=wallet_name)


def _check_renamed_symbols() -> None:
    renamed_currencies = Currency.objects.filter(symbol__in=settings.RENAMED_SYMBOLS.keys())
    if len(renamed_currencies):
        logger.warning("Some currencies have been renamed.")
        for currency in renamed_currencies:
            logger.warning(f"Renaming: {currency.symbol} -> {settings.RENAMED_SYMBOLS[currency.symbol]}")
            currency.symbol = settings.RENAMED_SYMBOLS[currency.symbol]
            currency.save()


class Command(BaseCommand):
    def handle(self, *args, **options):
        _check_renamed_symbols()
        _create_initial_currencies()
        _create_admin_user()
        _create_initial_wallets()

        logger.info("Project initialized!")
