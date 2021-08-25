from django.db.models.signals import post_delete
from django.dispatch import receiver

from crypto_fifo_taxes.models.transaction import Transaction


@receiver(post_delete, sender=Transaction)
def post_delete_transaction_details(instance, **kwargs):
    if instance.from_detail:
        instance.from_detail.delete()
    if instance.to_detail:
        instance.to_detail.delete()
    if instance.fee_detail:
        instance.fee_detail.delete()
