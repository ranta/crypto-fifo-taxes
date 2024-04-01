import logging
import sys
from datetime import datetime, timedelta

from crypto_fifo_taxes.models import Transaction

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)


def print_time_elapsed(func):
    """Print how long executing the function took"""

    def wrapper(*args, **kwargs):
        logger.info(f"Starting `{func.__name__}`!")
        start_time = datetime.now()
        func(*args, **kwargs)
        logger.info(f"`{func.__name__}` complete! Time elapsed: {datetime.now() - start_time}")

    return wrapper


def print_time_elapsed_new_transactions(func):
    def wrapper(*args, **kwargs):
        start_time = datetime.now()
        transactions_count = Transaction.objects.count()
        logger.info(f"Starting `{func.__name__}`!")

        func(*args, **kwargs)

        elapsed = datetime.now() - start_time
        elapsed -= timedelta(microseconds=elapsed.microseconds)
        new_transactions = Transaction.objects.count() - transactions_count

        if elapsed or new_transactions:
            logger.info(
                f"`{func.__name__}` complete! Time elapsed: {elapsed}. Transactions created {new_transactions}."
            )
        else:
            # Simpler print when function was executed quickly and no new transactions were created
            logger.info("...done")

    return wrapper


def print_entry_and_exit(logger: logging.Logger, function_name: str):
    def decorator(func):
        def print_box_message_top(message: str) -> None:
            logger.info("┌" + "─" * (len(message) + 2) + "┐")
            logger.info("│ " + message)

        def print_box_message_bottom(message: str) -> None:
            logger.info("│ " + message)
            logger.info("└" + "─" * (len(message) + 2) + "┘")

        def wrapper(*args, **kwargs):
            print_box_message_top(f"Starting `{function_name}`")
            func(*args, **kwargs)
            print_box_message_bottom(f"Finished `{function_name}`")

        return wrapper

    return decorator
