class InsufficientFundsError(Exception):
    """Not enough funds in wallet to withdraw the given quantity"""


class MissingPriceHistoryError(Exception):
    pass


class MissingCostBasisError(Exception):
    pass


class PdfException(Exception):
    pass


class TooManyResultsError(Exception):
    """Too many results returned from a binance endpoint, timeframe should be smaller"""


class EtherscanException(Exception):
    pass


class InvalidImportRowException(Exception):
    pass


class CoinGeckoAPIException(Exception):
    pass


class CoinGeckoMissingCurrency(CoinGeckoAPIException):
    pass


class CoinGeckoMultipleMatchingCurrenciesCurrency(CoinGeckoAPIException):
    pass


class SnapshotHelperException(Exception):
    pass
