
from django.core.management import BaseCommand

from crypto_fifo_taxes.utils.helpers.snapshot_helper import SnapshotHelper
from crypto_fifo_taxes.utils.wrappers import print_time_elapsed


class Command(BaseCommand):
    @print_time_elapsed
    def handle(self, *args, **kwargs):
        snapshot_helper = SnapshotHelper()
        snapshot_helper.generate_snapshots()
        snapshot_helper.generate_snapshot_balances()
        snapshot_helper.calculate_snapshots_worth()
