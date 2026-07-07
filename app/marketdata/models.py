from dataclasses import dataclass


@dataclass
class StockData:
    symbol: str
    price: float | None = None
    currency: str | None = None
    source: str | None = None