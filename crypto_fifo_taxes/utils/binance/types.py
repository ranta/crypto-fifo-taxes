from typing import TypedDict


class BinanceFlexibleInterest(TypedDict):
    time: int
    asset: str
    rewards: str


class BinanceFlexibleInterestHistoryResponse(TypedDict):
    total: int
    rows: list[BinanceFlexibleInterest]


class BinanceLockedInterest(TypedDict):
    time: int
    asset: str
    amount: str


class BinanceLockedInterestHistoryResponse(TypedDict):
    total: int
    rows: list[BinanceLockedInterest]
