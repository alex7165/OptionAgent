from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math

from app.analysis.assignment_backtest import AssignmentBacktestOutcome
from app.analysis.management_action import ManagementAction, ThreatenedSide
from app.analysis.stock_hedge_backtest import StockHedgeBacktestOutcome


@dataclass(frozen=True, slots=True)
class ManagementActionOutcome:
    """Comparable result of one management action at one decision point.

    ``total_profit_loss`` remains optional because the current historical data
    does not contain historical option prices for every action. Such outcomes
    are retained as evidence, but cannot be labelled as the financially best
    action until their complete P/L is available.
    """

    action: ManagementAction
    threatened_side: ThreatenedSide
    decision_date: date
    evaluation_date: date
    capital_required: float
    maximum_drawdown: float
    total_profit_loss: float | None
    complete_profit_loss: bool
    observations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name, value in (
            ("capital_required", self.capital_required),
            ("maximum_drawdown", self.maximum_drawdown),
        ):
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if self.capital_required < 0:
            raise ValueError("capital_required must not be negative")
        if self.evaluation_date < self.decision_date:
            raise ValueError("evaluation_date must not be before decision_date")
        if self.total_profit_loss is not None and not math.isfinite(
            self.total_profit_loss
        ):
            raise ValueError("total_profit_loss must be finite when supplied")
        if self.complete_profit_loss != (self.total_profit_loss is not None):
            raise ValueError(
                "complete_profit_loss must match total_profit_loss availability"
            )
        if self.action not in ManagementAction.allowed_for_side(
            self.threatened_side
        ):
            raise ValueError(
                f"action {self.action.value} is not valid for "
                f"{self.threatened_side.value} side"
            )

    @classmethod
    def from_stock_hedge(
        cls,
        outcome: StockHedgeBacktestOutcome,
    ) -> ManagementActionOutcome:
        return cls(
            action=outcome.action,
            threatened_side=ThreatenedSide.CALL,
            decision_date=outcome.decision_date,
            evaluation_date=outcome.exit_date,
            capital_required=outcome.capital_required,
            maximum_drawdown=outcome.maximum_stock_drawdown,
            total_profit_loss=None,
            complete_profit_loss=False,
            observations=outcome.observations,
        )

    @classmethod
    def from_assignment(
        cls,
        outcome: AssignmentBacktestOutcome,
    ) -> ManagementActionOutcome:
        return cls(
            action=outcome.action,
            threatened_side=ThreatenedSide.PUT,
            decision_date=outcome.assignment_date,
            evaluation_date=outcome.evaluation_date,
            capital_required=outcome.capital_required,
            maximum_drawdown=outcome.maximum_drawdown,
            total_profit_loss=outcome.total_profit_loss,
            complete_profit_loss=True,
            observations=(
                "Andienung einschließlich der explizit übergebenen "
                "Covered-Call-Verkäufe bewertet.",
            ),
        )
