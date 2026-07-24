from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.analysis.management_action import ManagementAction, ThreatenedSide


@dataclass(frozen=True, slots=True)
class ManagementDecisionContext:
    """Information known when a management action is considered.

    Future outcome data deliberately does not belong in this object.
    """

    decision_date: date
    trading_day_index: int
    threatened_side: ThreatenedSide
    action: ManagementAction
    underlying_price: float
    short_strike: float
    days_to_expiration: int
    short_option_delta: float | None = None
    stock_hedge_shares_per_contract: int | None = None
    expected_move_percent: float | None = None
    iv_rank: float | None = None
    iv_percentile: float | None = None
    entry_strategy: str | None = None

    def __post_init__(self) -> None:
        if self.trading_day_index <= 0:
            raise ValueError("trading_day_index must be greater than zero")
        if self.underlying_price <= 0:
            raise ValueError("underlying_price must be greater than zero")
        if self.short_strike <= 0:
            raise ValueError("short_strike must be greater than zero")
        if self.days_to_expiration < 0:
            raise ValueError("days_to_expiration must not be negative")
        if self.action not in ManagementAction.allowed_for_side(
            self.threatened_side
        ):
            raise ValueError(
                f"action {self.action.value} is not valid for "
                f"{self.threatened_side.value} side"
            )
        if self.short_option_delta is not None and not (
            0.0 <= abs(self.short_option_delta) <= 1.0
        ):
            raise ValueError("short_option_delta absolute value must be <= 1")
        for name, value in (
            ("iv_rank", self.iv_rank),
            ("iv_percentile", self.iv_percentile),
        ):
            if value is not None and not (0.0 <= value <= 100.0):
                raise ValueError(f"{name} must be between 0 and 100")
        if self.expected_move_percent is not None and self.expected_move_percent < 0:
            raise ValueError("expected_move_percent must not be negative")
        if self.entry_strategy is not None:
            normalized_strategy = self.entry_strategy.strip().lower()
            object.__setattr__(self, "entry_strategy", normalized_strategy or None)

        if self.action is ManagementAction.BUY_STOCK_HEDGE:
            if self.threatened_side is not ThreatenedSide.CALL:
                raise ValueError(
                    "buy_stock_hedge is only valid for the call side"
                )
            if self.short_option_delta is None:
                raise ValueError(
                    "short_option_delta is required for buy_stock_hedge"
                )
            expected_shares = round(abs(self.short_option_delta) * 100)
            if self.stock_hedge_shares_per_contract is None:
                object.__setattr__(
                    self,
                    "stock_hedge_shares_per_contract",
                    expected_shares,
                )
        elif self.stock_hedge_shares_per_contract is not None:
            raise ValueError(
                "stock_hedge_shares_per_contract is only valid for "
                "buy_stock_hedge"
            )
