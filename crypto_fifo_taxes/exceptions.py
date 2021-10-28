class MissingPriceError(Exception):
    pass


class MissingPriceHistoryError(Exception):
    pass


class MissingCostBasis(Exception):
    pass


class PdfException(Exception):
    pass


class TooManyResultsError(Exception):
    """Too many results returned from a binance endpoint, timeframe should be smaller"""


class CoinGeckoMissingCurrency(Exception):
    pass
