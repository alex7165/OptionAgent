from datetime import date

from app.analysis.repair_strategy_backtest import (
    RepairSide,
    RepairStrategyBacktestAnalyzer,
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


def test_no_touch_means_no_repair() -> None:
    result = RepairStrategyBacktestAnalyzer().analyze(
        selection(),
        (bar(14, 97, 103, 101),),
        reference_price=100,
    )

    assert result.triggered is False


def test_put_touch_moves_put_outward_and_evaluates_remaining_path() -> None:
    result = RepairStrategyBacktestAnalyzer(
        outward_buffer_percent=2.5
    ).analyze(
        selection(),
        (
            bar(14, 94, 102, 96),
            bar(15, 93, 101, 98),
        ),
        reference_price=100,
    )

    assert result.triggered is True
    assert result.threatened_side is RepairSide.PUT
    assert result.original_strike == 95
    assert result.repaired_strike == 92.5
    assert result.repaired_strike_touched is False
    assert result.repaired_strike_finished_outside is False


def test_call_touch_moves_call_outward() -> None:
    result = RepairStrategyBacktestAnalyzer(
        outward_buffer_percent=2.0
    ).analyze(
        selection(),
        (
            bar(14, 98, 106, 105.5),
            bar(15, 99, 108, 107.5),
        ),
        reference_price=100,
    )

    assert result.threatened_side is RepairSide.CALL
    assert result.repaired_strike == 107
    assert result.repaired_strike_touched is True
    assert result.repaired_strike_finished_outside is True
