import logging
import os

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import BaseCommand

from crypto_fifo_taxes.models import Currency, Wallet
from crypto_fifo_taxes.utils.currency import get_default_fiat

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        # Create required FIAT currencies
        for symbol, data in settings.ALL_FIAT_CURRENCIES.items():
            Currency.objects.update_or_create(
                symbol=symbol,
                defaults={
                    "name": data["name"],
                    "cg_id": data["cg_id"],
                    "is_fiat": True,
                },
            )

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

        wallet_names = [w.strip() for w in os.environ.get("WALLET_NAMES").split(",")]
        for wallet_name in wallet_names:
            Wallet.objects.get_or_create(user=admin_user, name=wallet_name, fiat=get_default_fiat())
        logger.info("Project initialized!")
