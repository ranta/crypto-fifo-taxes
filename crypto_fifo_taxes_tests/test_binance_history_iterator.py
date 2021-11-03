from collections import namedtuple
from datetime import datetime, timedelta

import pytest

from crypto_fifo_taxes.exceptions import TooManyResultsError
from crypto_fifo_taxes.utils.binance.binance_api import binance_history_iterator, from_timestamp

HistoryOutput = namedtuple("HistoryOutput", "start_time num_results")


@pytest.mark.django_db
def test_binance_history_iterator():
    expected_output = [
        # Ok results
        HistoryOutput(datetime(2018, 1, 1), 5),
        HistoryOutput(datetime(2018, 1, 1) + timedelta(days=30), 2),
        # Too many results, loop through again with smaller period
        HistoryOutput(datetime(2018, 1, 1) + timedelta(days=60), 10),
        HistoryOutput(datetime(2018, 1, 1) + timedelta(days=60), 5),
        HistoryOutput(datetime(2018, 1, 1) + timedelta(days=75), 6),
        # Ok results again
        HistoryOutput(datetime(2018, 1, 1) + timedelta(days=90), 1),
        # Too many results, loop through again with smaller period x2
        HistoryOutput(datetime(2018, 1, 1) + timedelta(days=120), 10),
        HistoryOutput(datetime(2018, 1, 1) + timedelta(days=120), 10),
        HistoryOutput(datetime(2018, 1, 1) + timedelta(days=120), 5),
        HistoryOutput(datetime(2018, 1, 1) + timedelta(days=127), 5),
        HistoryOutput(datetime(2018, 1, 1) + timedelta(days=134), 5),
        HistoryOutput(datetime(2018, 1, 1) + timedelta(days=141), 5),
        HistoryOutput(datetime(2018, 1, 1) + timedelta(days=148), 5),
        # Ok again
        HistoryOutput(datetime(2018, 1, 1) + timedelta(days=150), 1),
    ]

    def iterator_func(startTime: int, endTime: int):
        """
        Simulate a function that fetches data from a Binance API endpoint
        If over 10 results are returned, assume there is missing data and raise an error
        """

        nonlocal i  # Use outer scope variable
        response = expected_output[i]
        converted_start_time = from_timestamp(startTime).replace(tzinfo=None)

        if response.num_results >= 10:
            i = i + 1
            raise TooManyResultsError

        assert converted_start_time == expected_output[i].start_time, i

        i = i + 1
        return [startTime]

    i = 0  # Iteration counter
    start_date = datetime(2018, 1, 1)
    output = binance_history_iterator(
        iterator_func,
        period_length=30,
        start_date=start_date,
        end_date=start_date + timedelta(days=180),
    )
    assert len(list(output)) == 11
