from __future__ import annotations

from datetime import date

from app.analysis.entry_decision_snapshot import EntryDecisionSnapshot
from app.analysis.management_outcome import ManagementOutcome
from app.analysis.management_strategy import (
    build_management_outcome,
    historical_strikes,
)
from app.marketdata.price_history_provider import DailyBar


class CloseDay1Strategy:
    """Close the historical trade at the first reaction-session close."""

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
        short_put_strike, short_call_strike = historical_strikes(
            entry,
            reference_price,
        )
        return build_management_outcome(
            strategy_name="close_after_reaction",
            entry_day=1,
            exit_day=1,
            exit_reason="reaction_day_close",
            evaluation_bars=(reaction_bar,),
            exit_close=reaction_bar.close,
            reference_price=reference_price,
            short_put_strike=short_put_strike,
            short_call_strike=short_call_strike,
            made_all_time_high=made_all_time_high,
        )
