# Generated by Django 3.2.4 on 2021-08-18 14:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crypto_fifo_taxes', '0005_fix_enumfield_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='order_id',
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
        migrations.AddField(
            model_name='transaction',
            name='tx_id',
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
    ]
