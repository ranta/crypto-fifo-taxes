class InsufficientFundsError(Exception):
    """Not enough funds in wallet to withdraw the given quantity"""


class MissingPriceError(Exception):
    pass


class MissingPriceHistoryError(Exception):
    pass


class MissingCostBasisError(Exception):
    pass


class PdfException(Exception):
    pass


class TooManyResultsError(Exception):
    """Too many results returned from a binance endpoint, timeframe should be smaller"""


class CoinGeckoMissingCurrency(Exception):
    pass


class EtherscanException(Exception):
    pass


class InvalidImportRowException(Exception):
    pass
