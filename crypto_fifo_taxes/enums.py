from django.utils.translation import gettext as _
from enumfields import Enum


class TradeType(Enum):
    BUY = 1
    SELL = 2

    class Labels:
        BUY = _("Buy")
        SELL = _("Sell")


class TransactionType(Enum):
    UNKNOWN = 0
    TRADE = 1  # Exchanging one crypto to another
    BANK_DEPOSIT = 2  # Deposits from bank account to the wallet
    MINING = 3
    REWARD = 4  # Staking, airdrop etc.
    SPENDING = 5  # Paying for things with crypto
    SWAP = 6  # Name change etc.

    class Labels:
        UNKNOWN = _("Unknown")
        TRADE = _("Trade")
        BANK_DEPOSIT = _("Bank Deposit")
        MINING = _("Mining")
        REWARD = _("Reward")
        SPENDING = _("Spending")
        SWAP = _("Swap")
