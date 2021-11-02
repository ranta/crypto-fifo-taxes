from django.urls import path

from crypto_fifo_taxes.views.graph import GraphView
from crypto_fifo_taxes.views.transactions import TransactionListView

urlpatterns = [
    path("transactions/", TransactionListView.as_view()),
    path("graph/", GraphView.as_view()),
]
