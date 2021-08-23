from binance import Client


class BinanceClient(Client):
    # FIAT
    def get_fiat_deposits(self, **params):
        """
        https://binance-docs.github.io/apidocs/spot/en/#get-swap-history-user_data
        """
        params["transactionType"] = 0
        return self._request_margin_api("get", "fiat/orders", True, data=params)

    def get_fiat_withdraws(self, **params):
        """
        https://binance-docs.github.io/apidocs/spot/en/#get-swap-history-user_data
        """
        params["transactionType"] = 1
        return self._request_margin_api("get", "fiat/orders", True, data=params)

    def get_fiat_buys(self, **params):
        """
        https://binance-docs.github.io/apidocs/spot/en/#get-fiat-payments-history-user_data
        """
        params["transactionType"] = 0
        return self._request_margin_api("get", "fiat/payments", True, data=params)

    def get_fiat_sells(self, **params):
        """
        https://binance-docs.github.io/apidocs/spot/en/#get-fiat-payments-history-user_data
        """
        params["transactionType"] = 1
        return self._request_margin_api("get", "fiat/payments", True, data=params)
