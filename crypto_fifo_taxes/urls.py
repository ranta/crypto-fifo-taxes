from django.urls import path

from crypto_fifo_taxes.views.transactions import transaction_list

urlpatterns = [
    path("transactions/", transaction_list),
]
