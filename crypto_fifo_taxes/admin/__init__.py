from django.contrib import admin
from django.contrib.admin import ModelAdmin

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
admin.site.register(Wallet)
admin.site.register(Transaction)
admin.site.register(TransactionDetail)


@admin.register(CurrencyPrice)
class CurrencyPriceAdmin(ModelAdmin):
    list_display = [
        "currency",
        "date",
        "price",
    ]
    list_filter = ["currency", "date"]


class SnapshotBalanceInline(admin.TabularInline):
    model = SnapshotBalance
    extra = 0
    show_change_link = False
    can_delete = False


@admin.register(Snapshot)
class SnapshotAdmin(ModelAdmin):
    list_display = [
        "date",
        "worth",
        "cost_basis",
        "deposits",
    ]
    inlines = [SnapshotBalanceInline]
    ordering = ["-date"]
