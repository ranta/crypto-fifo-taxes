# Generated by Django 3.2.4 on 2021-08-24 15:07

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('crypto_fifo_taxes', '0007_transaction_ordering'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='transaction',
            name='order_id',
        ),
    ]
