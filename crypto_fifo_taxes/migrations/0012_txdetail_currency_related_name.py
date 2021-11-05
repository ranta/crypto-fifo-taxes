# Generated by Django 3.2.8 on 2021-10-28 14:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('crypto_fifo_taxes', '0011_ordering'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='snapshot',
            options={'ordering': ('date',)},
        ),
        migrations.AlterField(
            model_name='transactiondetail',
            name='currency',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='transaction_details', to='crypto_fifo_taxes.currency'),
        ),
    ]