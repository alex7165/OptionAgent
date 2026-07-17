from datetime import date

import pytest

from app.analysis.entry_decision_snapshot import EntryDecisionSnapshot
from app.analysis.strategies.hold_to_friday_strategy import HoldToFridayStrategy
from app.analysis.strategy import Strategy
from app.marketdata.price_history_provider import DailyBar


def test_holds_through_last_available_earnings_week_session():
    entry = EntryDecisionSnapshot(
        "GS",
        date(2026, 7, 13),
        date(2026, 7, 14),
        date(2026, 7, 17),
        Strategy.SHORT_STRANGLE,
        100,
        90,
        105,
    )
    bars = (
        DailyBar(date(2025, 7, 15), 108, 110, 107, 109, 1),
        DailyBar(date(2025, 7, 16), 106, 108, 103, 104, 1),
        DailyBar(date(2025, 7, 17), 102, 104, 100, 101, 1),
        DailyBar(date(2025, 7, 18), 100, 102, 98, 100, 1),
    )

    outcome = HoldToFridayStrategy().simulate(
        entry=entry,
        report_date=date(2025, 7, 15),
        reference_price=100,
        reaction_bar=bars[0],
        after_reaction=bars,
        made_all_time_high=False,
    )

    assert outcome.strategy_name == "hold_to_friday"
    assert outcome.exit_day == 4
    assert outcome.exit_reason == "earnings_week_end"
    assert outcome.final_move_percent == pytest.approx(0.0)
    assert outcome.max_favorable_move == pytest.approx(10.0)
    assert outcome.max_adverse_move == pytest.approx(-2.0)
    assert outcome.finished_inside_strikes is True
