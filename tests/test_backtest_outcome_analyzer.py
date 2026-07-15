from datetime import date

import pytest

from app.analysis.backtest_outcome_analyzer import BacktestOutcomeAnalyzer
from app.analysis.strike_selection import StrikeSelection
from app.analysis.strategy import Strategy
from app.marketdata.models import OptionQuote
from app.marketdata.price_history_provider import DailyBar


def quote(option_type: str, strike: float) -> OptionQuote:
    return OptionQuote(
        symbol="TEST",
        expiration=date(2026, 7, 17),
        strike=strike,
        option_type=option_type,
        bid=1.0,
        ask=1.2,
        last=1.1,
        volume=100,
        open_interest=500,
    )


def selection() -> StrikeSelection:
    return StrikeSelection(
        put=quote("put", 95.0),
        call=quote("call", 105.0),
        put_target=95.0,
        call_target=105.0,
        strategy=Strategy.SHORT_STRANGLE,
    )


def bar(day: int, high: float, low: float, close: float) -> DailyBar:
    return DailyBar(
        date=date(2026, 7, day),
        open=100.0,
        high=high,
        low=low,
        close=close,
        volume=1_000_000,
    )


def test_trade_finishes_inside_without_touch() -> None:
    result = BacktestOutcomeAnalyzer().analyze(
        selection=selection(),
        daily_bars=(
            bar(14, high=103.0, low=97.0, close=101.0),
            bar(15, high=104.0, low=96.0, close=102.0),
        ),
        reference_price=100.0,
        exit_trading_day_index=2,
    )

    assert result.finished_inside_short_strikes is True
    assert result.put_touched is False
    assert result.call_touched is False
    assert result.put_finished_outside is False
    assert result.call_finished_outside is False
    assert result.exit_close == 102.0
    assert result.holding_days == 2
    assert result.max_adverse_move_percent == pytest.approx(-4.0)
    assert result.max_favorable_move_percent == pytest.approx(4.0)


def test_touch_is_recorded_even_when_exit_finishes_inside() -> None:
    result = BacktestOutcomeAnalyzer().analyze(
        selection=selection(),
        daily_bars=(
            bar(14, high=106.0, low=94.0, close=100.0),
            bar(15, high=103.0, low=98.0, close=101.0),
        ),
        reference_price=100.0,
        exit_trading_day_index=2,
    )

    assert result.put_touched is True
    assert result.call_touched is True
    assert result.finished_inside_short_strikes is True


def test_exit_close_outside_call_is_recorded() -> None:
    result = BacktestOutcomeAnalyzer().analyze(
        selection=selection(),
        daily_bars=(
            bar(14, high=106.0, low=98.0, close=104.0),
            bar(15, high=109.0, low=102.0, close=107.0),
            bar(16, high=111.0, low=105.0, close=110.0),
        ),
        reference_price=100.0,
        exit_trading_day_index=2,
    )

    assert result.exit_date == date(2026, 7, 15)
    assert result.call_finished_outside is True
    assert result.finished_inside_short_strikes is False
    assert result.call_touched is True


def test_only_bars_up_to_selected_exit_are_used() -> None:
    result = BacktestOutcomeAnalyzer().analyze(
        selection=selection(),
        daily_bars=(
            bar(14, high=103.0, low=97.0, close=101.0),
            bar(15, high=104.0, low=96.0, close=102.0),
            bar(16, high=120.0, low=80.0, close=110.0),
        ),
        reference_price=100.0,
        exit_trading_day_index=2,
    )

    assert result.put_touched is False
    assert result.call_touched is False
    assert result.max_adverse_move_percent == pytest.approx(-4.0)
    assert result.max_favorable_move_percent == pytest.approx(4.0)


def test_rejects_missing_requested_exit_day() -> None:
    with pytest.raises(
        ValueError,
        match="do not contain the requested exit trading day",
    ):
        BacktestOutcomeAnalyzer().analyze(
            selection=selection(),
            daily_bars=(bar(14, high=103.0, low=97.0, close=101.0),),
            reference_price=100.0,
            exit_trading_day_index=2,
        )


def test_rejects_incomplete_selection() -> None:
    incomplete = StrikeSelection(
        put=None,
        call=quote("call", 105.0),
        put_target=95.0,
        call_target=105.0,
    )

    with pytest.raises(
        ValueError,
        match="selection must contain both short strikes",
    ):
        BacktestOutcomeAnalyzer().analyze(
            selection=incomplete,
            daily_bars=(bar(14, high=103.0, low=97.0, close=101.0),),
            reference_price=100.0,
            exit_trading_day_index=1,
        )
