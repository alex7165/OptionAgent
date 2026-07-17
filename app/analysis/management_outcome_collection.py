from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.analysis.management_outcome import ManagementOutcome


@dataclass(frozen=True, slots=True)
class ManagementOutcomeCollection:
    symbol: str
    earnings_date: date
    reference_price: float
    outcomes: tuple[ManagementOutcome, ...]

    def __post_init__(self) -> None:
        normalized_symbol = self.symbol.strip().upper()
        if not normalized_symbol:
            raise ValueError("symbol must not be empty")
        if self.reference_price <= 0:
            raise ValueError("reference_price must be greater than zero")

        object.__setattr__(self, "symbol", normalized_symbol)
