import datetime


def utc_datetime() -> datetime.datetime:
    """Get current datetime in UTC."""
    return datetime.datetime.now(tz=datetime.UTC)


def utc_date() -> datetime.date:
    """Get current date in UTC."""
    return utc_datetime().date()


def utc_start_of_day(date: datetime.date | datetime.datetime | None = None) -> datetime.datetime:
    """Get the start of day (00:00:00) as datetime for the given date (of today if None) in UTC."""
    if isinstance(date, datetime.datetime):
        date = date.astimezone(datetime.UTC).date()
    if date is None:
        date = utc_date()
    return datetime.datetime.combine(date, datetime.time.min, tzinfo=datetime.UTC)


def utc_end_of_day(date: datetime.date | datetime.datetime | None = None) -> datetime.datetime:
    """Get the end of day (23:59:59.999...) as datetime for the given date (of today if None) in UTC."""
    if isinstance(date, datetime.datetime):
        date = date.astimezone(datetime.UTC).date()
    if date is None:
        date = utc_date()
    return datetime.datetime.combine(date, datetime.time.max, tzinfo=datetime.UTC)
