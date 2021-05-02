from django.contrib.auth.models import User
from django.core.management import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):

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
