# Generated by Django 5.0.2 on 2024-02-23 20:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crypto_fifo_taxes", "0013_increase_currency_name_max_length"),
    ]

    operations = [
        migrations.AlterField(
            model_name="currency",
            name="cg_id",
            field=models.CharField(max_length=64, unique=True),
        ),
        migrations.AlterField(
            model_name="transaction",
            name="tx_id",
            field=models.CharField(blank=True, default="", max_length=256),
        ),
    ]