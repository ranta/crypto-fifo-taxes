from django.urls import path

from crypto_fifo_taxes.views.graph import snapshot_graph
from crypto_fifo_taxes.views.transactions import TransactionListView

urlpatterns = [
    path("transactions/", TransactionListView.as_view()),
    path("graph/", snapshot_graph),
]
