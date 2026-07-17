from __future__ import annotations

from datetime import date
from typing import Protocol

from app.analysis.entry_decision_snapshot import EntryDecisionSnapshot
from app.analysis.management_outcome import ManagementOutcome
from app.analysis.management_strategy_score import ManagementStrategyScore
from app.marketdata.price_history_provider import DailyBar


class ManagementStrategy(Protocol):
    """Simulate one management decision for a comparable earnings case."""

    def simulate(
        self,
        *,
        entry: EntryDecisionSnapshot,
        report_date: date,
        reference_price: float,
        reaction_bar: DailyBar,
        after_reaction: tuple[DailyBar, ...],
        made_all_time_high: bool,
    ) -> ManagementOutcome:
        ...


def build_management_outcome(
    *,
    strategy_name: str,
    entry_day: int,
    exit_day: int,
    exit_reason: str,
    evaluation_bars: tuple[DailyBar, ...],
    exit_close: float,
    reference_price: float,
    short_put_strike: float,
    short_call_strike: float,
    made_all_time_high: bool,
) -> ManagementOutcome:
    if not evaluation_bars:
        raise ValueError("evaluation_bars must not be empty")

    maximum_move = max(bar.high / reference_price - 1 for bar in evaluation_bars)
    minimum_move = min(bar.low / reference_price - 1 for bar in evaluation_bars)
    final_move = (exit_close / reference_price - 1) * 100

    outcome = ManagementOutcome(
        strategy_name=strategy_name,
        entry_day=entry_day,
        exit_day=exit_day,
        exit_reason=exit_reason,
        max_adverse_move=minimum_move * 100,
        max_favorable_move=maximum_move * 100,
        finished_inside_strikes=(
            short_put_strike <= exit_close <= short_call_strike
        ),
        all_time_high_after_entry=made_all_time_high,
        final_move_percent=final_move,
    )
    return ManagementOutcome(
        strategy_name=outcome.strategy_name,
        entry_day=outcome.entry_day,
        exit_day=outcome.exit_day,
        exit_reason=outcome.exit_reason,
        max_adverse_move=outcome.max_adverse_move,
        max_favorable_move=outcome.max_favorable_move,
        finished_inside_strikes=outcome.finished_inside_strikes,
        all_time_high_after_entry=outcome.all_time_high_after_entry,
        final_move_percent=outcome.final_move_percent,
        score=ManagementStrategyScore.from_outcome(outcome),
    )


def historical_strikes(
    entry: EntryDecisionSnapshot,
    reference_price: float,
) -> tuple[float, float]:
    return (
        reference_price * entry.short_put_strike / entry.reference_price,
        reference_price * entry.short_call_strike / entry.reference_price,
    )
