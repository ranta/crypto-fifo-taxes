import logging
import sys

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)


def log_progress(message: str, current: int, maximum: int, interval: int | None = None) -> None:
    percentage_str = f"{current / maximum * 100:>4.1f}%"
    if interval is not None and current % interval != 0:
        return
    logger.info(f"{message} ({percentage_str})")
