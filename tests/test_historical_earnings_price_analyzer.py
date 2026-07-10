from datetime import date

import pytest

from app.analysis.historical_earnings_analysis import (
    HistoricalEarningsPriceSeries,
)
from app.analysis.historical_earnings_price_analyzer import (
    HistoricalEarningsPriceAnalyzer,
)
from app.analysis.price_series_analyzer import PriceSeriesAnalyzer
from app.marketdata.earnings_api_provider import (
    HistoricalEarningsReaction,
)
from app.marketdata.price_history_provider import DailyBar


def make_earnings_reaction() -> HistoricalEarningsReaction:
    return HistoricalEarningsReaction(
        report_date=date(2026, 4, 16),
        symbol="NFLX",
        eps_surprise_percent=-7.9,
        eps_yoy_percent=-89.4,
        eps_beat=False,
        revenue_surprise_percent=0.6,
        revenue_yoy_percent=16.2,
        revenue_beat=True,
        reactions=(),
    )


def make_price_series() -> HistoricalEarningsPriceSeries:
    return HistoricalEarningsPriceSeries(
        earnings=make_earnings_reaction(),
        daily_bars=(
            DailyBar(
                date=date(2026, 4, 17),
                open=96.0,
                high=102.0,
                low=94.0,
                close=100.0,
                volume=1_000_000,
            ),
            DailyBar(
                date=date(2026, 4, 20),
                open=100.0,
                high=108.0,
                low=92.0,
                close=95.0,
                volume=900_000,
            ),
        ),
    )


def test_analyzes_historical_earnings_price_series() -> None:
    price_series = make_price_series()

    analysis = HistoricalEarningsPriceAnalyzer(
        price_series_analyzer=PriceSeriesAnalyzer(),
    ).analyze(
        price_series=price_series,
        reference_price=100.0,
    )

    assert analysis.earnings is price_series.earnings
    assert analysis.price_analysis.reference_price == 100.0
    assert analysis.price_analysis.first_date == date(2026, 4, 17)
    assert analysis.price_analysis.last_date == date(2026, 4, 20)
    assert analysis.price_analysis.max_gain_percent == pytest.approx(8.0)
    assert analysis.price_analysis.max_loss_percent == pytest.approx(-8.0)


def test_passes_explicit_reference_price_to_price_series_analyzer() -> None:
    analysis = HistoricalEarningsPriceAnalyzer(
        price_series_analyzer=PriceSeriesAnalyzer(),
    ).analyze(
        price_series=make_price_series(),
        reference_price=80.0,
    )

    assert analysis.price_analysis.reference_price == 80.0
    assert analysis.price_analysis.max_gain_percent == pytest.approx(35.0)
    assert analysis.price_analysis.max_loss_percent == pytest.approx(15.0)


def test_rejects_empty_price_series() -> None:
    price_series = HistoricalEarningsPriceSeries(
        earnings=make_earnings_reaction(),
        daily_bars=(),
    )

    with pytest.raises(
        ValueError,
        match="daily_bars must not be empty",
    ):
        HistoricalEarningsPriceAnalyzer(
            price_series_analyzer=PriceSeriesAnalyzer(),
        ).analyze(
            price_series=price_series,
            reference_price=100.0,
        )