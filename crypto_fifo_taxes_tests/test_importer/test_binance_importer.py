from decimal import Decimal

import pytest

from crypto_fifo_taxes.models import CurrencyPair, Transaction
from crypto_fifo_taxes.utils.binance.binance_api import bstrptime, from_timestamp
from crypto_fifo_taxes.utils.binance.binance_importer import (
    import_deposits,
    import_dividends,
    import_dust,
    import_pair_trades,
    import_withdrawals,
)
from crypto_fifo_taxes.utils.currency import get_or_create_currency
from crypto_fifo_taxes_tests.factories import CryptoCurrencyFactory, CurrencyPriceFactory, WalletFactory
from crypto_fifo_taxes_tests.utils import WalletHelper


@pytest.mark.django_db()
def test_binance_deposit_import():
    wallet = WalletFactory.create()
    deposits = [
        {
            "amount": "0.00999800",
            "coin": "PAXG",
            "network": "ETH",
            "status": 1,
            "address": "0x788cabe9236ce061e5a892e1a59395a81fc8d62c",
            "addressTag": "",
            "txId": "0xaad4654a3234aa6118af9b4b335f5ae81c360b2394721c019b5d1e75328b09f3",
            "insertTime": 1599621997000,
            "transferType": 0,
            "confirmTimes": "12/12",
        },
        {
            "amount": "0.50000000",
            "coin": "IOTA",
            "network": "IOTA",
            "status": 1,
            "address": "SIZ9VLMHWATXKV99LH99CIGFJFUMLEHGWVZVNNZXRJJVWBPHYWPPBOSDORZ9EQSHCZAMPVAPGFYQAUUV9DROOXJLNW",
            "addressTag": "",
            "txId": "ESBFVQUTPIWQNJSPXFNHNYHSQNTGKRVKPRABQWTAXCDWOAKDKYWPTVG9BGXNVNKTLEJGESAVXIKIZ9999",
            "insertTime": 1599620082000,
            "transferType": 0,
            "confirmTimes": "1/1",
        },
    ]
    for deposit in deposits:
        crypto = CryptoCurrencyFactory.create(symbol=deposit["coin"])
        CurrencyPriceFactory.create(currency=crypto, fiat=wallet.fiat, date=from_timestamp(deposit["insertTime"]))

    import_deposits(wallet, deposits)
    assert Transaction.objects.all().count() == 2
    assert deposits[0]["txId"] in Transaction.objects.values_list("tx_id", flat=True)


@pytest.mark.django_db()
def test_binance_withdrawal_import():
    wallet = WalletFactory.create()
    wallet_helper = WalletHelper(wallet)
    withdrawals = [
        {
            "address": "0x94df8b352de7f46f64b01d3666bf6e936e44ce60",
            "amount": "8.91000000",
            "applyTime": "2019-10-12 11:12:02",
            "coin": "USDT",
            "id": "b6ae22b3aa844210a7041aee7589627c",
            "withdrawOrderId": "WITHDRAWtest123",
            "network": "ETH",
            "transferType": 0,
            "status": 6,
            "transactionFee": "0.004",
            "txId": "0xb5ef8c13b968a406cc62a93a8bd80f9e9a906ef1b3fcf20a2e48573c17659268",
        },
        {
            "address": "1FZdVHtiBqMrWdjPyRPULCUceZPJ2WLCsB",
            "amount": "0.00150000",
            "applyTime": "2019-09-24 12:43:45",
            "coin": "BTC",
            "id": "156ec387f49b41df8724fa744fa82719",
            "network": "BTC",
            "status": 6,
            "transactionFee": "0.0004",
            "transferType": 0,
            "txId": "60fd9007ebfddc753455f95fafa808c4302c836e4d1eebc5a132c36c1d8ac354",
        },
    ]
    for withdrawal in withdrawals:
        crypto = CryptoCurrencyFactory.create(symbol=withdrawal["coin"])
        tx_time = bstrptime(withdrawal["applyTime"])
        CurrencyPriceFactory.create(currency=crypto, fiat=wallet.fiat, date=tx_time.date())
        wallet_helper.deposit(crypto, Decimal(withdrawal["amount"]), tx_time)

    import_withdrawals(wallet, withdrawals)

    for withdrawal in withdrawals:
        assert wallet.get_current_balance(withdrawal["coin"]) == -Decimal(withdrawal["transactionFee"])
    assert withdrawals[0]["txId"] in Transaction.objects.values_list("tx_id", flat=True)


@pytest.mark.django_db()
def test_binance_trade_import():
    wallet = WalletFactory.create()
    nano_eth_trades = [
        {
            "symbol": "NANOETH",
            "id": 137423,
            "orderId": 470859,
            "orderListId": -1,
            "price": "0.01448100",
            "qty": "3.00000000",
            "quoteQty": "0.04344300",
            "commission": "0.00300000",
            "commissionAsset": "NANO",
            "time": 1518002736381,
            "isBuyer": True,
            "isMaker": False,
            "isBestMatch": True,
        },
        {
            "symbol": "NANOETH",
            "id": 291506,
            "orderId": 1185932,
            "orderListId": -1,
            "price": "0.00935000",
            "qty": "7.99000000",
            "quoteQty": "0.07470650",
            "commission": "0.00002241",
            "commissionAsset": "ETH",
            "time": 1518650278882,
            "isBuyer": False,
            "isMaker": True,
            "isBestMatch": True,
        },
    ]
    trading_pair = CurrencyPair.objects.get_or_create(
        symbol="NANOETH",
        defaults={
            "buy": get_or_create_currency("NANO"),
            "sell": get_or_create_currency("ETH"),
        },
    )[0]

    import_pair_trades(wallet, trading_pair, nano_eth_trades)

    assert Transaction.objects.count() == 2
    assert wallet.get_current_balance("NANO") == Decimal("3.00000000") - Decimal("7.99000000") - Decimal("0.00300000")


@pytest.mark.django_db()
def test_binance_dust_import():
    wallet = WalletFactory.create()
    converts = [
        {
            "operateTime": 1615985535000,
            "totalTransferedAmount": "0.00132256",  # Total transferred BNB amount for this exchange.
            "totalServiceChargeAmount": "0.00002699",  # Total service charge amount for this exchange.
            "transId": 45178372831,
            "userAssetDribbletDetails": [  # Details of  this exchange.
                {
                    "transId": 4359321,
                    "serviceChargeAmount": "0.000009",
                    "amount": "0.0009",
                    "operateTime": 1615985535000,
                    "transferedAmount": "0.000441",
                    "fromAsset": "USDT",
                },
                {
                    "transId": 4359321,
                    "serviceChargeAmount": "0.00001799",
                    "amount": "0.0009",
                    "operateTime": 1615985535000,
                    "transferedAmount": "0.00088156",
                    "fromAsset": "ETH",
                },
            ],
        },
        {
            "operateTime": 1616203180000,
            "totalTransferedAmount": "0.00058795",
            "totalServiceChargeAmount": "0.000012",
            "transId": 4357015,
            "userAssetDribbletDetails": [
                {
                    "transId": 4357015,
                    "serviceChargeAmount": "0.00001",
                    "amount": "0.001",
                    "operateTime": 1616203180000,
                    "transferedAmount": "0.00049",
                    "fromAsset": "USDT",
                },
                {
                    "transId": 4357015,
                    "serviceChargeAmount": "0.000002",
                    "amount": "0.0001",
                    "operateTime": 1616203180000,
                    "transferedAmount": "0.00009795",
                    "fromAsset": "ETH",
                },
            ],
        },
    ]

    import_dust(wallet, converts)

    assert Transaction.objects.count() == 4

    sum_bnb = Decimal(0)
    for convert in converts:
        for detail in convert["userAssetDribbletDetails"]:
            sum_bnb = sum_bnb + Decimal(detail["transferedAmount"]) - Decimal(detail["serviceChargeAmount"])
    assert wallet.get_current_balance("BNB") == sum_bnb


@pytest.mark.django_db()
def test_binance_dividend_import():
    wallet = WalletFactory.create()
    dividends = [
        {
            "amount": "10.00000000",
            "asset": "BETH",
            "divTime": 1563189166000,
            "enInfo": "ETH 2.0 Staking",
            "tranId": 2968885921,
        },
        {
            "amount": "10.00000000",
            "asset": "BETH",
            "divTime": 1563189165000,
            "enInfo": "ETH 2.0 Staking",
            "tranId": 2968885920,
        },
    ]

    import_dividends(wallet, dividends)

    assert Transaction.objects.count() == 2
    assert wallet.get_current_balance("BETH") == Decimal(20)
