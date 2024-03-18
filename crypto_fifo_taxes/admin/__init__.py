from django.contrib import admin

from crypto_fifo_taxes.models import (
    Currency,
    CurrencyPair,
    CurrencyPrice,
    Snapshot,
    SnapshotBalance,
    Transaction,
    TransactionDetail,
    Wallet,
)

admin.site.register(Currency)
admin.site.register(CurrencyPair)
admin.site.register(CurrencyPrice)
admin.site.register(Wallet)
admin.site.register(Transaction)
admin.site.register(TransactionDetail)
admin.site.register(Snapshot)
admin.site.register(SnapshotBalance)
