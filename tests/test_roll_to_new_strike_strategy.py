from datetime import date

import pytest

from app.analysis.entry_decision_snapshot import EntryDecisionSnapshot
from app.analysis.strategies.roll_to_new_strike_strategy import (
    RollToNewStrikeStrategy,
)
from app.analysis.strategy import Strategy
from app.marketdata.price_history_provider import DailyBar


def entry() -> EntryDecisionSnapshot:
    return EntryDecisionSnapshot(
        "GS",
        date(2026, 7, 13),
        date(2026, 7, 14),
        date(2026, 7, 17),
        Strategy.SHORT_STRANGLE,
        100,
        90,
        105,
    )


def test_rolls_breached_call_from_reaction_close_and_holds_to_friday():
    bars = (
        DailyBar(date(2025, 7, 15), 108, 110, 107, 109, 1),
        DailyBar(date(2025, 7, 16), 110, 113, 109, 112, 1),
        DailyBar(date(2025, 7, 17), 111, 114, 110, 113, 1),
        DailyBar(date(2025, 7, 18), 112, 115, 111, 114, 1),
    )

    outcome = RollToNewStrikeStrategy().simulate(
        entry=entry(),
        report_date=date(2025, 7, 15),
        reference_price=100,
        reaction_bar=bars[0],
        after_reaction=bars,
        made_all_time_high=True,
    )

    assert outcome.strategy_name == "roll_to_new_strike"
    assert outcome.entry_day == 1
    assert outcome.exit_day == 4
    assert outcome.exit_reason == "rolled_call_to_new_strike"
    assert outcome.final_move_percent == pytest.approx(14.0)
    assert outcome.finished_inside_strikes is True
    assert outcome.max_favorable_move == pytest.approx(15.0)
    assert outcome.all_time_high_after_entry is True


def test_does_not_roll_when_neither_short_strike_is_breached():
    bars = (
        DailyBar(date(2025, 7, 15), 100, 104, 96, 102, 1),
        DailyBar(date(2025, 7, 16), 101, 103, 97, 102, 1),
        DailyBar(date(2025, 7, 17), 101, 104, 98, 103, 1),
        DailyBar(date(2025, 7, 18), 102, 104, 99, 103, 1),
    )

    outcome = RollToNewStrikeStrategy().simulate(
        entry=entry(),
        report_date=date(2025, 7, 15),
        reference_price=100,
        reaction_bar=bars[0],
        after_reaction=bars,
        made_all_time_high=False,
    )

    assert outcome.exit_reason == "no_strike_breach"
    assert outcome.finished_inside_strikes is True


def test_rolls_breached_put_from_reaction_close():
    bars = (
        DailyBar(date(2025, 7, 15), 91, 93, 88, 89, 1),
        DailyBar(date(2025, 7, 16), 87, 90, 85, 86, 1),
        DailyBar(date(2025, 7, 17), 86, 89, 84, 88, 1),
        DailyBar(date(2025, 7, 18), 88, 91, 87, 90, 1),
    )

    outcome = RollToNewStrikeStrategy().simulate(
        entry=entry(),
        report_date=date(2025, 7, 15),
        reference_price=100,
        reaction_bar=bars[0],
        after_reaction=bars,
        made_all_time_high=False,
    )

    assert outcome.exit_reason == "rolled_put_to_new_strike"
    assert outcome.finished_inside_strikes is True
