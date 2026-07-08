from dataclasses import dataclass, field
from datetime import date


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
class OptionQuote:
    symbol: str
    expiration: date
    strike: float
    option_type: str
    bid: float | None = None
    ask: float | None = None
    last: float | None = None
    volume: int | None = None
    open_interest: int | None = None

    @property
    def mid(self) -> float | None:
        if self.bid is None or self.ask is None:
            return None

        return (self.bid + self.ask) / 2

    @property
    def bid_ask_spread(self) -> float | None:
        if self.bid is None or self.ask is None:
            return None

        return self.ask - self.bid

    @property
    def bid_ask_spread_percent(self) -> float | None:
        if self.mid in (None, 0):
            return None

        return self.bid_ask_spread / self.mid

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


@dataclass
class MarketSnapshot:
    symbol: str
    quote: Quote | None = None
    earnings: EarningsEvent | None = None
    option_chain: OptionChain | None = None
    news: list[str] = field(default_factory=list)

@dataclass(slots=True)
class ExpirationChain:
    symbol: str
    expiration: date
    quotes: list[OptionQuote]