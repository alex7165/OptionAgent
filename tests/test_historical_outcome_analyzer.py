from datetime import date

import pytest

from app.analysis.daily_move_analyzer import DailyMove
from app.analysis.historical_earnings_price_analyzer import (
    HistoricalEarningsPriceAnalysis,
)
from app.analysis.historical_outcome_analyzer import (
    HistoricalOutcomeAnalyzer,
)
from app.analysis.price_series_analyzer import (
    PriceSeriesAnalysis,
)
from app.marketdata.earnings_api_provider import (
    HistoricalEarningsReaction,
)


def make_price_analysis(
    daily_moves: tuple[DailyMove, ...],
) -> HistoricalEarningsPriceAnalysis:
    return HistoricalEarningsPriceAnalysis(
        earnings=HistoricalEarningsReaction(
            report_date=date(2026, 4, 16),
            symbol="NFLX",
            eps_surprise_percent=5.0,
            eps_yoy_percent=10.0,
            eps_beat=True,
            revenue_surprise_percent=2.0,
            revenue_yoy_percent=8.0,
            revenue_beat=True,
            reactions=(),
        ),
        price_analysis=PriceSeriesAnalysis(
            reference_price=100.0,
            first_date=date(2026, 4, 17),
            last_date=date(2026, 4, 21),
            first_open=104.0,
            first_close=106.0,
            last_close=103.0,
            highest_high=115.0,
            lowest_low=91.0,
            max_gain_percent=15.0,
            max_loss_percent=-9.0,
        ),
        daily_moves=daily_moves,
    )


def make_daily_moves() -> tuple[DailyMove, ...]:
    return (
        DailyMove(
            trading_day_index=1,
            date=date(2026, 4, 17),
            open_percent=4.0,
            high_percent=10.0,
            low_percent=-2.0,
            close_percent=6.0,
        ),
        DailyMove(
            trading_day_index=2,
            date=date(2026, 4, 20),
            open_percent=7.0,
            high_percent=15.0,
            low_percent=-5.0,
            close_percent=8.0,
        ),
        DailyMove(
            trading_day_index=3,
            date=date(2026, 4, 21),
            open_percent=5.0,
            high_percent=9.0,
            low_percent=-9.0,
            close_percent=3.0,
        ),
    )


def test_analyzes_outcome_until_selected_exit_day() -> None:
    outcome = HistoricalOutcomeAnalyzer().analyze(
        price_analysis=make_price_analysis(
            make_daily_moves()
        ),
        exit_trading_day_index=2,
    )

    assert outcome.exit_trading_day_index == 2
    assert outcome.exit_date == date(2026, 4, 20)
    assert outcome.exit_close_percent == pytest.approx(8.0)
    assert outcome.highest_percent_until_exit == pytest.approx(
        15.0
    )
    assert outcome.lowest_percent_until_exit == pytest.approx(
        -5.0
    )
    assert outcome.trading_days_observed == 2


def test_excludes_moves_after_selected_exit_day() -> None:
    outcome = HistoricalOutcomeAnalyzer().analyze(
        price_analysis=make_price_analysis(
            make_daily_moves()
        ),
        exit_trading_day_index=1,
    )

    assert outcome.exit_close_percent == pytest.approx(6.0)
    assert outcome.highest_percent_until_exit == pytest.approx(
        10.0
    )
    assert outcome.lowest_percent_until_exit == pytest.approx(
        -2.0
    )
    assert outcome.trading_days_observed == 1


def test_analyzes_complete_available_period() -> None:
    outcome = HistoricalOutcomeAnalyzer().analyze(
        price_analysis=make_price_analysis(
            make_daily_moves()
        ),
        exit_trading_day_index=3,
    )

    assert outcome.exit_date == date(2026, 4, 21)
    assert outcome.exit_close_percent == pytest.approx(3.0)
    assert outcome.highest_percent_until_exit == pytest.approx(
        15.0
    )
    assert outcome.lowest_percent_until_exit == pytest.approx(
        -9.0
    )
    assert outcome.trading_days_observed == 3


@pytest.mark.parametrize(
    "exit_trading_day_index",
    (
        0,
        -1,
    ),
)
def test_rejects_invalid_exit_day_index(
    exit_trading_day_index: int,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "exit_trading_day_index must be at least 1"
        ),
    ):
        HistoricalOutcomeAnalyzer().analyze(
            price_analysis=make_price_analysis(
                make_daily_moves()
            ),
            exit_trading_day_index=exit_trading_day_index,
        )


def test_rejects_analysis_without_daily_moves() -> None:
    with pytest.raises(
        ValueError,
        match="price_analysis must contain daily moves",
    ):
        HistoricalOutcomeAnalyzer().analyze(
            price_analysis=make_price_analysis(()),
            exit_trading_day_index=1,
        )


def test_rejects_missing_exit_day() -> None:
    daily_moves = (
        DailyMove(
            trading_day_index=1,
            date=date(2026, 4, 17),
            open_percent=4.0,
            high_percent=10.0,
            low_percent=-2.0,
            close_percent=6.0,
        ),
        DailyMove(
            trading_day_index=3,
            date=date(2026, 4, 21),
            open_percent=5.0,
            high_percent=9.0,
            low_percent=-9.0,
            close_percent=3.0,
        ),
    )

    with pytest.raises(
        ValueError,
        match="No daily move found for exit trading day 2",
    ):
        HistoricalOutcomeAnalyzer().analyze(
            price_analysis=make_price_analysis(
                daily_moves
            ),
            exit_trading_day_index=2,
        )


def test_rejects_duplicate_exit_day() -> None:
    duplicate_move = DailyMove(
        trading_day_index=1,
        date=date(2026, 4, 20),
        open_percent=5.0,
        high_percent=11.0,
        low_percent=-3.0,
        close_percent=7.0,
    )

    daily_moves = (
        make_daily_moves()[0],
        duplicate_move,
    )

    with pytest.raises(
        ValueError,
        match=(
            "Multiple daily moves found for exit trading day 1"
        ),
    ):
        HistoricalOutcomeAnalyzer().analyze(
            price_analysis=make_price_analysis(
                daily_moves
            ),
            exit_trading_day_index=1,
        )