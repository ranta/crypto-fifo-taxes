# Generated by Django 5.0.2 on 2024-03-30 21:34
from django.conf import settings
from django.db import migrations


def remove_non_default_prices(apps, schema_editor):
    CurrencyPrice = apps.get_model("crypto_fifo_taxes", "CurrencyPrice")

    CurrencyPrice.objects.exclude(fiat__symbol=settings.DEFAULT_FIAT_SYMBOL).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("crypto_fifo_taxes", "0018_remove_user_connections"),
    ]

    operations = [
        migrations.RunPython(remove_non_default_prices, reverse_code=migrations.RunPython.noop),
        migrations.AlterUniqueTogether(
            name="currencyprice",
            unique_together={("currency", "date")},
        ),
        migrations.RemoveField(
            model_name="wallet",
            name="fiat",
        ),
        migrations.RemoveField(
            model_name="currencyprice",
            name="fiat",
        ),
    ]
