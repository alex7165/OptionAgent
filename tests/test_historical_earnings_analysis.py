from datetime import date

from app.analysis.historical_earnings_analysis import (
    HistoricalEarningsAnalysis,
    HistoricalEarningsOutcome,
    HistoricalEarningsPriceSeries,
)
from app.marketdata.earnings_api_provider import (
    EarningsReactionDay,
    HistoricalEarningsReaction,
)
from app.marketdata.price_history_provider import DailyBar


def test_calculates_partial_recovery():
    outcome = HistoricalEarningsOutcome(
        first_day_move_percent=20.0,
        expiration_week_move_percent=8.0,
    )

    assert outcome.recovery_ratio == 0.6
    assert outcome.continued_move is False


def test_detects_continued_move():
    outcome = HistoricalEarningsOutcome(
        first_day_move_percent=-20.0,
        expiration_week_move_percent=-27.0,
    )

    assert outcome.recovery_ratio == 0.0
    assert outcome.continued_move is True


def test_treats_direction_reversal_as_full_recovery():
    outcome = HistoricalEarningsOutcome(
        first_day_move_percent=12.0,
        expiration_week_move_percent=-2.0,
    )

    assert outcome.recovery_ratio == 1.0
    assert outcome.continued_move is False


def test_exposes_move_collections():
    analysis = HistoricalEarningsAnalysis(
        outcomes=(
            HistoricalEarningsOutcome(
                first_day_move_percent=20.0,
                expiration_week_move_percent=8.0,
            ),
            HistoricalEarningsOutcome(
                first_day_move_percent=-10.0,
                expiration_week_move_percent=-14.0,
            ),
        )
    )

    assert analysis.first_day_moves.maximum_up_move_percent == 20.0
    assert analysis.first_day_moves.maximum_down_move_percent == -10.0
    assert analysis.expiration_week_moves.maximum_down_move_percent == -14.0
    assert analysis.recovery_ratios == (0.6, 0.0)
    assert analysis.continued_move_flags == (False, True)


def test_stores_complete_price_series_for_earnings_event():
    earnings = HistoricalEarningsReaction(
        report_date=date(2026, 4, 16),
        symbol="NFLX",
        eps_surprise_percent=-7.9,
        eps_yoy_percent=-89.4,
        eps_beat=False,
        revenue_surprise_percent=0.6,
        revenue_yoy_percent=16.2,
        revenue_beat=True,
        reactions=(
            EarningsReactionDay(
                date=date(2026, 4, 17),
                open=96.37,
                high=98.74,
                low=95.10,
                close=97.31,
                volume=125_958_732,
                price_change_percent=-9.72,
            ),
        ),
    )

    daily_bars = (
        DailyBar(
            date=date(2026, 4, 17),
            open=96.37,
            high=98.74,
            low=95.10,
            close=97.31,
            volume=125_958_732,
        ),
        DailyBar(
            date=date(2026, 4, 20),
            open=97.14,
            high=97.60,
            low=93.54,
            close=94.83,
            volume=63_298_300,
        ),
        DailyBar(
            date=date(2026, 4, 21),
            open=95.10,
            high=99.20,
            low=94.80,
            close=98.75,
            volume=52_000_000,
        ),
        DailyBar(
            date=date(2026, 4, 22),
            open=99.00,
            high=101.50,
            low=97.90,
            close=100.80,
            volume=48_000_000,
        ),
    )

    series = HistoricalEarningsPriceSeries(
        earnings=earnings,
        daily_bars=daily_bars,
    )

    analysis = HistoricalEarningsAnalysis(
        price_series=(series,),
    )

    assert analysis.price_series == (series,)
    assert analysis.price_series[0].earnings.symbol == "NFLX"
    assert analysis.price_series[0].earnings.report_date == date(
        2026,
        4,
        16,
    )
    assert analysis.price_series[0].daily_bars == daily_bars
    assert len(analysis.price_series[0].daily_bars) == 4