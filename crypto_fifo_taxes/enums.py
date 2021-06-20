from django.utils.translation import gettext as _
from enumfields import Enum


class TransactionType(Enum):
    UNKNOWN = 0
    DEPOSIT = 1
    WITHDRAW = 2
    TRADE = 3  # Trade between two crypto currencies
    TRANSFER = 4  # Transfer from one wallet to another
    SWAP = 5  # Name change etc. that doesn't realize value

    class Labels:
        UNKNOWN = _("Unknown")
        DEPOSIT = _("Deposit")
        WITHDRAW = _("Withdraw")
        TRADE = _("Trade")
        TRANSFER = _("Transfer")
        SWAP = _("Swap")


class TransactionLabel(Enum):
    UNKNOWN = 0
    MINING = 1
    AIRDROP = 2
    REWARD = 3  # Staking, interest etc.
    SPENDING = 4  # Paying for things with crypto

    class Labels:
        UNKNOWN = _("Unknown")
        MINING = _("Mining")
        AIRDROP = _("Airdrop")
        REWARD = _("Reward")
        SPENDING = _("Spending")
