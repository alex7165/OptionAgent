from datetime import date

import pytest

from app.analysis.entry_decision_snapshot import EntryDecisionSnapshot
from app.analysis.strategies.close_day1_strategy import CloseDay1Strategy
from app.analysis.strategy import Strategy
from app.marketdata.price_history_provider import DailyBar


def test_closes_at_first_reaction_session():
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
    reaction = DailyBar(date(2025, 7, 15), 108, 110, 107, 109, 1)

    outcome = CloseDay1Strategy().simulate(
        entry=entry,
        report_date=date(2025, 7, 15),
        reference_price=100,
        reaction_bar=reaction,
        after_reaction=(reaction,),
        made_all_time_high=True,
    )

    assert outcome.strategy_name == "close_after_reaction"
    assert outcome.exit_day == 1
    assert outcome.exit_reason == "reaction_day_close"
    assert outcome.final_move_percent == pytest.approx(9.0)
    assert outcome.max_favorable_move == pytest.approx(10.0)
    assert outcome.max_adverse_move == pytest.approx(7.0)
    assert outcome.finished_inside_strikes is False
    assert outcome.all_time_high_after_entry is True
