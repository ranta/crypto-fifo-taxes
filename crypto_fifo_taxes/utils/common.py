import logging


def log_progress(logger: logging.Logger, message: str, current: int, maximum: int, interval: int | None = None) -> None:
    percentage_str = f"{current / maximum * 100:>4.1f}%"
    if interval is not None and current % interval != 0 and current != maximum:
        return
    logger.info(f"│ {message} ({percentage_str})")
