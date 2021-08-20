from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import BaseCommand

from crypto_fifo_taxes.models import Currency, Wallet
from crypto_fifo_taxes.utils.currency import get_default_fiat


class Command(BaseCommand):
    def handle(self, *args, **options):
        # Create required FIAT currencies
        for symbol, name in settings.ALL_FIAT_CURRENCIES.items():
            Currency.objects.get_or_create(symbol=symbol, defaults=dict(name=name, is_fiat=True))

        # Create admin user
        admin_user, admin_created = User.objects.get_or_create(
            username="admin",
            defaults=dict(
                email="admin@example.com",
                first_name="Admin",
                last_name="Superuser",
                is_staff=True,
                is_active=True,
                is_superuser=True,
            ),
        )
        if admin_created:
            admin_user.set_password("admin")
            admin_user.save()
            Wallet.objects.create(
                user=admin_user,
                name="Default Wallet",
                fiat=get_default_fiat(),
            )
