from __future__ import annotations

from datetime import date

from app.analysis.entry_decision_snapshot import EntryDecisionSnapshot
from app.analysis.management_outcome import ManagementOutcome
from app.analysis.management_strategy import (
    build_management_outcome,
    historical_strikes,
)
from app.marketdata.price_history_provider import DailyBar


class HoldToFridayStrategy:
    """Keep the historical trade open through the earnings-week close."""

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
        if not after_reaction:
            raise ValueError("after_reaction must not be empty")

        short_put_strike, short_call_strike = historical_strikes(
            entry,
            reference_price,
        )
        return build_management_outcome(
            strategy_name="hold_to_friday",
            entry_day=1,
            exit_day=len(after_reaction),
            exit_reason="earnings_week_end",
            evaluation_bars=after_reaction,
            exit_close=after_reaction[-1].close,
            reference_price=reference_price,
            short_put_strike=short_put_strike,
            short_call_strike=short_call_strike,
            made_all_time_high=made_all_time_high,
        )
