from django.urls import path

from crypto_fifo_taxes.views.graph import GraphView
from crypto_fifo_taxes.views.index import IndexView
from crypto_fifo_taxes.views.management import ManagementView
from crypto_fifo_taxes.views.management_commands import CalculateSnapshotsView, FetchPricesView, FetchTransactionsView
from crypto_fifo_taxes.views.transactions import TransactionListView, TransactionMiningListView

urlpatterns = [
    path("", IndexView.as_view(), name="index"),
    path("transactions/", TransactionListView.as_view(), name="transactions"),
    path("transactions/mining/", TransactionMiningListView.as_view(), name="transactions_mining"),
    path("graph/", GraphView.as_view(), name="graph"),
    path("management/", ManagementView.as_view(), name="management"),
    path("management/fetch_transactions/", FetchTransactionsView.as_view(), name="fetch_transactions"),
    path("management/fetch_prices/", FetchPricesView.as_view(), name="fetch_prices"),
    path("management/calculate_snapshots/", CalculateSnapshotsView.as_view(), name="calculate_snapshots"),
]
