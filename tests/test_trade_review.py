from datetime import date

import pytest

from app.analysis.strike_selection import StrikeSelection
from app.analysis.strategy import Strategy
from app.analysis.trade_review import TradeReviewAnalyzer
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


def test_reviews_selected_exit_and_all_alternatives() -> None:
    review = TradeReviewAnalyzer().analyze(
        selection=selection(),
        daily_bars=(
            bar(14, high=102.0, low=98.0, close=101.0),
            bar(15, high=103.0, low=97.0, close=102.0),
            bar(16, high=104.0, low=96.0, close=103.0),
        ),
        reference_price=100.0,
        selected_exit_trading_day_index=2,
    )

    assert review.selected_exit.trading_day_index == 2
    assert tuple(
        item.trading_day_index for item in review.alternative_exits
    ) == (1, 3)
    assert review.selected_exit.finished_inside_short_strikes is True


def test_assesses_clean_inside_exit_as_very_good() -> None:
    review = TradeReviewAnalyzer().analyze(
        selection=selection(),
        daily_bars=(bar(14, high=103.0, low=97.0, close=101.0),),
        reference_price=100.0,
        selected_exit_trading_day_index=1,
    )

    assert review.assessment == (
        "Sehr gut: innerhalb der Short-Strikes ohne Berührung"
    )


def test_reports_touch_risk_even_when_exit_finishes_inside() -> None:
    review = TradeReviewAnalyzer().analyze(
        selection=selection(),
        daily_bars=(bar(14, high=106.0, low=98.0, close=101.0),),
        reference_price=100.0,
        selected_exit_trading_day_index=1,
    )

    assert review.assessment == (
        "Erfolgreich, aber mit zwischenzeitlichem Touch-Risiko"
    )
    assert review.selected_exit.call_touched is True


def test_reports_strike_violation_at_selected_exit() -> None:
    review = TradeReviewAnalyzer().analyze(
        selection=selection(),
        daily_bars=(bar(14, high=108.0, low=100.0, close=107.0),),
        reference_price=100.0,
        selected_exit_trading_day_index=1,
    )

    assert review.assessment == "Strike am gewählten Exit verletzt"
    assert review.selected_exit.call_finished_outside is True


def test_identifies_earlier_safe_and_later_riskier_exit() -> None:
    review = TradeReviewAnalyzer().analyze(
        selection=selection(),
        daily_bars=(
            bar(14, high=102.0, low=98.0, close=101.0),
            bar(15, high=104.0, low=97.0, close=102.0),
            bar(16, high=106.0, low=96.0, close=103.0),
            bar(17, high=109.0, low=98.0, close=107.0),
        ),
        reference_price=100.0,
        selected_exit_trading_day_index=2,
    )

    assert any("früherer Exit" in item for item in review.observations)
    assert any("späterer Exit" in item for item in review.observations)


def test_rejects_missing_selected_exit_day() -> None:
    with pytest.raises(
        ValueError,
        match="do not contain the selected exit trading day",
    ):
        TradeReviewAnalyzer().analyze(
            selection=selection(),
            daily_bars=(bar(14, high=102.0, low=98.0, close=101.0),),
            reference_price=100.0,
            selected_exit_trading_day_index=2,
        )
