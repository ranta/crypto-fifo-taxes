from django.apps import AppConfig


class CryptoFifoTaxesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "crypto_fifo_taxes"

    def ready(self):
        from crypto_fifo_taxes import signals  # noqa
