from datetime import date

import pytest

from app.analysis.historical_management_strategy_simulator import (
    HistoricalManagementStrategy,
    HistoricalManagementStrategySimulator,
)
from app.analysis.strategy_selector import Strategy
from app.analysis.strike_selection import StrikeSelection
from app.marketdata.models import OptionQuote
from app.marketdata.price_history_provider import DailyBar


def quote(option_type: str, strike: float) -> OptionQuote:
    return OptionQuote(
        symbol="TEST",
        expiration=date(2026, 7, 17),
        strike=strike,
        option_type=option_type,
    )


def selection() -> StrikeSelection:
    return StrikeSelection(
        put=quote("put", 95),
        call=quote("call", 105),
        put_target=95,
        call_target=105,
        strategy=Strategy.SHORT_STRANGLE,
    )


def bar(day: int, low: float, high: float, close: float) -> DailyBar:
    return DailyBar(
        date=date(2026, 7, day),
        open=100,
        high=high,
        low=low,
        close=close,
        volume=1000,
    )


def test_simulates_close_and_hold_baselines_from_same_reaction_day() -> None:
    outcomes = HistoricalManagementStrategySimulator().simulate_baselines(
        selection=selection(),
        daily_bars=(
            bar(14, 103, 108, 107),
            bar(15, 104, 110, 109),
            bar(16, 101, 107, 103),
            bar(17, 98, 104, 100),
        ),
        reference_price=100,
    )

    close, hold = outcomes

    assert close.strategy is HistoricalManagementStrategy.CLOSE_AFTER_REACTION
    assert close.decision_date == date(2026, 7, 14)
    assert close.evaluation_end_date == date(2026, 7, 14)
    assert close.evaluation_end_move_percent == pytest.approx(7.0)
    assert close.finished_inside_short_strikes is False
    assert close.maximum_move_after_decision_percent == pytest.approx(10.0)
    assert close.minimum_move_after_decision_percent == pytest.approx(-2.0)

    assert hold.strategy is HistoricalManagementStrategy.HOLD_TO_FRIDAY
    assert hold.decision_date == date(2026, 7, 14)
    assert hold.evaluation_end_date == date(2026, 7, 17)
    assert hold.evaluation_end_move_percent == pytest.approx(0.0)
    assert hold.finished_inside_short_strikes is True
    assert hold.maximum_move_after_decision_percent == pytest.approx(10.0)
    assert hold.minimum_move_after_decision_percent == pytest.approx(-2.0)


def test_supports_reaction_day_later_in_series() -> None:
    outcomes = HistoricalManagementStrategySimulator().simulate_baselines(
        selection=selection(),
        daily_bars=(
            bar(13, 99, 101, 100),
            bar(14, 104, 107, 106),
            bar(15, 102, 108, 103),
        ),
        reference_price=100,
        reaction_trading_day_index=2,
    )

    close, hold = outcomes

    assert close.decision_trading_day_index == 2
    assert close.decision_date == date(2026, 7, 14)
    assert close.maximum_move_after_decision_percent == pytest.approx(8.0)
    assert hold.evaluation_end_date == date(2026, 7, 15)


def test_rejects_unsorted_bars() -> None:
    with pytest.raises(
        ValueError,
        match="daily_bars must be ordered by ascending unique date",
    ):
        HistoricalManagementStrategySimulator().simulate_baselines(
            selection=selection(),
            daily_bars=(
                bar(15, 99, 101, 100),
                bar(14, 99, 101, 100),
            ),
            reference_price=100,
        )
