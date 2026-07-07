from dataclasses import dataclass
from datetime import date


@dataclass
class StockData:
    symbol: str
    price: float | None = None
    currency: str | None = None
    source: str | None = None


@dataclass
class Quote:
    symbol: str
    price: float
    currency: str
    source: str


@dataclass
class OptionContract:
    symbol: str
    expiration: date
    strike: float
    option_type: str
    bid: float | None = None
    ask: float | None = None
    last: float | None = None
    implied_volatility: float | None = None
    volume: int | None = None
    open_interest: int | None = None


@dataclass
class OptionChain:
    symbol: str
    expiration: date
    contracts: list[OptionContract]


@dataclass
class EarningsEvent:
    symbol: str
    report_date: date
    timing: str | None = None
    source: str | None = None