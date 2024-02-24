import logging
from functools import lru_cache

import requests
from django.conf import settings

from crypto_fifo_taxes.exceptions import EtherscanException

logger = logging.getLogger(__name__)


@lru_cache
def get_ethplorer_client():
    api_key = settings.ETHPLORER_API_KEY
    if api_key is None:
        api_key = "freekey"
        logger.warning("'ETHPLORER_API_KEY' environment variable is missing. Using 'freekey' instead.")
    return EtherscanClient(api_key)


class EtherscanClient:
    api_key = None
    known_pool_addresses = []

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._get_known_pool_addresses()

    def _get_known_pool_addresses(self) -> None:
        """Ethplorer private API endpoint to get addresses with `miner` tag"""
        url = "https://ethplorer.io/service/service.php?search=miner&sm=spt"
        results = requests.get(url, timeout=10).json()["results"]
        self.known_pool_addresses = [result[2] for result in results]

    def get_tx_info(self, tx_id: str) -> dict:
        url = f"https://api.ethplorer.io/getTxInfo/{tx_id}?apiKey={self.api_key}"
        return requests.get(url, timeout=10).json()

    def _is_real_tx_id(self, tx_id: str) -> bool:
        return len(tx_id) == 66 and tx_id.startswith("0x")

    def is_tx_from_mining_pool(self, tx_id: str) -> bool:
        if not self._is_real_tx_id(tx_id):
            return False

        tx_info = self.get_tx_info(tx_id)
        if "error" in tx_info:
            raise EtherscanException(tx_info, tx_id)
        if "from" in tx_info:
            from_address = tx_info["from"]
            return from_address in self.known_pool_addresses
        return False
