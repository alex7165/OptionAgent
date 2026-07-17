from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class TrainingExample:
    """One supervised training row for historical trade management."""

    symbol: str
    earnings_date: date
    report_timing: str
    reference_price: float
    entry_strategy: str
    expected_move_percent: float | None
    short_put_distance_percent: float
    short_call_distance_percent: float
    first_reaction_move_percent: float
    maximum_move_percent: float
    friday_close_move_percent: float
    made_all_time_high: bool
    best_management_strategy: str

    def __post_init__(self) -> None:
        normalized_symbol = self.symbol.strip().upper()
        if not normalized_symbol:
            raise ValueError("symbol must not be empty")
        if self.reference_price <= 0:
            raise ValueError("reference_price must be greater than zero")
        if not self.report_timing.strip():
            raise ValueError("report_timing must not be empty")
        if not self.entry_strategy.strip():
            raise ValueError("entry_strategy must not be empty")
        if not self.best_management_strategy.strip():
            raise ValueError("best_management_strategy must not be empty")

        object.__setattr__(self, "symbol", normalized_symbol)
        object.__setattr__(self, "report_timing", self.report_timing.strip().lower())
