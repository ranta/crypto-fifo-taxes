# Generated by Django 3.2.4 on 2021-08-18 11:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crypto_fifo_taxes', '0003_increase_decimal_precision'),
    ]

    operations = [
        migrations.AddField(
            model_name='currency',
            name='cg_id',
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
    ]
