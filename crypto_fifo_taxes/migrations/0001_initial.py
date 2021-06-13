# Generated by Django 3.2.3 on 2021-06-13 21:28

import crypto_fifo_taxes.enums
import crypto_fifo_taxes.utils.models
from decimal import Decimal
from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import enumfields.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Currency',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('symbol', models.CharField(max_length=30, unique=True, verbose_name='Symbol')),
                ('name', models.CharField(max_length=30, unique=True, verbose_name='Name')),
                ('icon', models.ImageField(blank=True, null=True, upload_to='coin_icons', verbose_name='Icon')),
                ('is_fiat', models.BooleanField(default=False, verbose_name='Is FIAT')),
            ],
        ),
        migrations.CreateModel(
            name='Wallet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='Wallet Name')),
                ('icon', models.ImageField(blank=True, null=True, upload_to='wallet_icons', verbose_name='Icon')),
                ('fiat', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wallets', to='crypto_fifo_taxes.currency', verbose_name='FIAT')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wallets', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='TransactionDetail',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', crypto_fifo_taxes.utils.models.TransactionDecimalField(decimal_places=10, default=Decimal('0'), max_digits=20, validators=[django.core.validators.MinValueValidator(Decimal('0'))])),
                ('cost_basis', crypto_fifo_taxes.utils.models.TransactionDecimalField(decimal_places=10, default=Decimal('0'), max_digits=20, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0'))])),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='+', to='crypto_fifo_taxes.currency')),
                ('wallet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transaction_details', to='crypto_fifo_taxes.wallet')),
            ],
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField()),
                ('transaction_type', enumfields.fields.EnumField(enum=crypto_fifo_taxes.enums.TransactionType, max_length=10)),
                ('transaction_label', enumfields.fields.EnumField(enum=crypto_fifo_taxes.enums.TransactionLabel, max_length=10)),
                ('description', models.TextField(blank=True, default='')),
                ('gain', crypto_fifo_taxes.utils.models.TransactionDecimalField(decimal_places=10, default=Decimal('0'), max_digits=20, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0'))])),
                ('fee_amount', crypto_fifo_taxes.utils.models.TransactionDecimalField(decimal_places=10, default=Decimal('0'), max_digits=20, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0'))])),
                ('tx_fee', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='fee_detail', to='crypto_fifo_taxes.transactiondetail')),
                ('tx_from', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='from_detail', to='crypto_fifo_taxes.transactiondetail')),
                ('tx_to', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='to_detail', to='crypto_fifo_taxes.transactiondetail')),
            ],
        ),
        migrations.CreateModel(
            name='CurrencyPrice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('price', crypto_fifo_taxes.utils.models.TransactionDecimalField(decimal_places=10, default=Decimal('0'), max_digits=20, validators=[django.core.validators.MinValueValidator(Decimal('0'))])),
                ('market_cap', crypto_fifo_taxes.utils.models.TransactionDecimalField(decimal_places=10, default=Decimal('0'), max_digits=20, validators=[django.core.validators.MinValueValidator(Decimal('0'))])),
                ('volume', crypto_fifo_taxes.utils.models.TransactionDecimalField(decimal_places=10, default=Decimal('0'), max_digits=20, validators=[django.core.validators.MinValueValidator(Decimal('0'))])),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='prices', to='crypto_fifo_taxes.currency', verbose_name='Currency')),
                ('fiat', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='crypto_fifo_taxes.currency', verbose_name='FIAT')),
            ],
            options={
                'unique_together': {('currency', 'date', 'fiat')},
            },
        ),
        migrations.CreateModel(
            name='CurrencyPair',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('symbol', models.CharField(max_length=30, unique=True)),
                ('buy', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='buy_pairs', to='crypto_fifo_taxes.currency')),
                ('sell', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sell_pairs', to='crypto_fifo_taxes.currency')),
            ],
            options={
                'unique_together': {('buy', 'sell')},
            },
        ),
    ]
