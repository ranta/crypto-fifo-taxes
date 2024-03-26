from binance import Client


class BinanceClient(Client):
    # FIAT
    def get_fiat_deposits(self, **params):
        """https://binance-docs.github.io/apidocs/spot/en/#get-swap-history-user_data"""
        params["transactionType"] = 0
        return self._request_margin_api("get", "fiat/orders", True, data=params)

    def get_fiat_withdraws(self, **params):
        """https://binance-docs.github.io/apidocs/spot/en/#get-swap-history-user_data"""
        params["transactionType"] = 1
        return self._request_margin_api("get", "fiat/orders", True, data=params)

    def get_fiat_buys(self, **params):
        """https://binance-docs.github.io/apidocs/spot/en/#get-fiat-payments-history-user_data"""
        params["transactionType"] = 0
        return self._request_margin_api("get", "fiat/payments", True, data=params)

    def get_fiat_sells(self, **params):
        """https://binance-docs.github.io/apidocs/spot/en/#get-fiat-payments-history-user_data"""
        params["transactionType"] = 1
        return self._request_margin_api("get", "fiat/payments", True, data=params)

    def get_flexible_interest_history(self, **params):
        """
        The old endpoint is deprecated, so we had to write our own method for this

        https://binance-docs.github.io/apidocs/spot/en/#get-flexible-redemption-record-user_data
        """
        return self._request_margin_api("get", "simple-earn/flexible/history/rewardsRecord", signed=True, data=params)

    def get_locked_interest_history(self, **params):
        """
        The old endpoint is deprecated, so we had to write our own method for this

        https://binance-docs.github.io/apidocs/spot/en/#get-locked-redemption-record-user_data
        """
        return self._request_margin_api("get", "simple-earn/locked/history/rewardsRecord", signed=True, data=params)

    def get_beth_interest_history(self, **params):
        """
        The old endpoint is deprecated, so we had to write our own method for this

        https://binance-docs.github.io/apidocs/spot/en/#get-locked-redemption-record-user_data
        """
        return self._request_margin_api("get", "eth-staking/eth/history/rewardsHistory", signed=True, data=params)

    def get_flexible_redemption_history(self, **params):
        """
        Get Flexible Redemption History

        https://binance-docs.github.io/apidocs/spot/en/#get-flexible-redemption-record-user_data
        """
        return self._request_margin_api(
            "get", "simple-earn/flexible/history/redemptionRecord", signed=True, data=params
        )
