from __future__ import annotations

from datetime import date

from app.analysis.entry_decision_snapshot import EntryDecisionSnapshot
from app.analysis.management_outcome import ManagementOutcome
from app.analysis.management_strategy import (
    build_management_outcome,
    historical_strikes,
)
from app.marketdata.price_history_provider import DailyBar


class RollToNewStrikeStrategy:
    """Recenter only the threatened short strike after the reaction-day close.

    This is an underlying-only simulation. It deliberately does not invent
    historical option prices or roll credits. The threatened short strike is
    moved to the reaction close plus the original percentage distance from the
    pre-earnings reference price; the opposite short strike remains unchanged.
    """

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
        put_breach = reaction_bar.low <= short_put_strike
        call_breach = reaction_bar.high >= short_call_strike

        exit_reason = "no_strike_breach"
        if put_breach or call_breach:
            threatened_side = self._threatened_side(
                reaction_bar=reaction_bar,
                short_put_strike=short_put_strike,
                short_call_strike=short_call_strike,
                put_breach=put_breach,
                call_breach=call_breach,
            )
            if threatened_side == "put":
                put_distance = entry.short_put_strike / entry.reference_price - 1
                short_put_strike = reaction_bar.close * (1 + put_distance)
                exit_reason = "rolled_put_to_new_strike"
            else:
                call_distance = entry.short_call_strike / entry.reference_price - 1
                short_call_strike = reaction_bar.close * (1 + call_distance)
                exit_reason = "rolled_call_to_new_strike"

        evaluation_bars = after_reaction[1:] or (reaction_bar,)
        return build_management_outcome(
            strategy_name="roll_to_new_strike",
            entry_day=1,
            exit_day=len(after_reaction),
            exit_reason=exit_reason,
            evaluation_bars=evaluation_bars,
            exit_close=after_reaction[-1].close,
            reference_price=reference_price,
            short_put_strike=short_put_strike,
            short_call_strike=short_call_strike,
            made_all_time_high=made_all_time_high,
        )

    @staticmethod
    def _threatened_side(
        *,
        reaction_bar: DailyBar,
        short_put_strike: float,
        short_call_strike: float,
        put_breach: bool,
        call_breach: bool,
    ) -> str:
        if put_breach and call_breach:
            put_breach_percent = short_put_strike / reaction_bar.low - 1
            call_breach_percent = reaction_bar.high / short_call_strike - 1
            return "put" if put_breach_percent >= call_breach_percent else "call"
        return "put" if put_breach else "call"
