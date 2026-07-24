from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.analysis.management_action import ManagementAction, ThreatenedSide


@dataclass(frozen=True, slots=True)
class ManagementActionTrainingExample:
    """One action-specific supervised row for trade-management learning."""

    symbol: str
    decision_date: date
    threatened_side: ThreatenedSide
    action: ManagementAction
    trading_day_index: int
    underlying_price: float
    short_strike: float
    strike_distance_percent: float
    days_to_expiration: int
    short_option_delta: float | None
    expected_move_percent: float | None
    iv_rank: float | None
    iv_percentile: float | None
    entry_strategy: str | None
    capital_required: float
    maximum_drawdown: float
    total_profit_loss: float | None
    complete_profit_loss: bool
    is_best_action: bool | None

    def __post_init__(self) -> None:
        normalized_symbol = self.symbol.strip().upper()
        if not normalized_symbol:
            raise ValueError("symbol must not be empty")
        if self.trading_day_index <= 0:
            raise ValueError("trading_day_index must be greater than zero")
        if self.underlying_price <= 0:
            raise ValueError("underlying_price must be greater than zero")
        if self.short_strike <= 0:
            raise ValueError("short_strike must be greater than zero")
        if self.days_to_expiration < 0:
            raise ValueError("days_to_expiration must not be negative")
        if self.capital_required < 0:
            raise ValueError("capital_required must not be negative")
        if self.complete_profit_loss != (self.total_profit_loss is not None):
            raise ValueError(
                "complete_profit_loss must match total_profit_loss availability"
            )
        if not self.complete_profit_loss and self.is_best_action is not None:
            raise ValueError(
                "incomplete outcomes must not receive a best-action label"
            )
        object.__setattr__(self, "symbol", normalized_symbol)
        if self.entry_strategy is not None:
            normalized_strategy = self.entry_strategy.strip().lower()
            object.__setattr__(self, "entry_strategy", normalized_strategy or None)
