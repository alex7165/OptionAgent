from datetime import date

import pytest

from app.analysis.historical_earnings_price_analyzer import (
    HistoricalEarningsPriceAnalysis,
)
from app.analysis.historical_price_statistics_analyzer import (
    HistoricalPriceStatisticsAnalyzer,
)
from app.analysis.price_series_analyzer import (
    PriceSeriesAnalysis,
)
from app.marketdata.earnings_api_provider import (
    HistoricalEarningsReaction,
)


def make_price_analysis(
    report_date: date,
    max_gain_percent: float,
    max_loss_percent: float,
) -> HistoricalEarningsPriceAnalysis:
    return HistoricalEarningsPriceAnalysis(
        earnings=HistoricalEarningsReaction(
            report_date=report_date,
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
            first_date=report_date,
            last_date=report_date,
            first_open=100.0,
            first_close=100.0,
            last_close=100.0,
            highest_high=100.0 + max_gain_percent,
            lowest_low=100.0 + max_loss_percent,
            max_gain_percent=max_gain_percent,
            max_loss_percent=max_loss_percent,
        ),
    )


def test_calculates_statistics_for_multiple_earnings() -> None:
    price_analyses = (
        make_price_analysis(
            report_date=date(2025, 7, 17),
            max_gain_percent=12.0,
            max_loss_percent=-8.0,
        ),
        make_price_analysis(
            report_date=date(2025, 10, 16),
            max_gain_percent=6.0,
            max_loss_percent=-14.0,
        ),
        make_price_analysis(
            report_date=date(2026, 1, 20),
            max_gain_percent=18.0,
            max_loss_percent=-5.0,
        ),
    )

    statistics = HistoricalPriceStatisticsAnalyzer().analyze(
        price_analyses
    )

    assert statistics.earnings_count == 3
    assert statistics.average_max_gain_percent == pytest.approx(
        12.0
    )
    assert statistics.average_max_loss_percent == pytest.approx(
        -9.0
    )
    assert statistics.highest_max_gain_percent == pytest.approx(
        18.0
    )
    assert statistics.worst_max_loss_percent == pytest.approx(
        -14.0
    )
    assert statistics.median_max_gain_percent == pytest.approx(
        12.0
    )
    assert statistics.median_max_loss_percent == pytest.approx(
        -8.0
    )


def test_calculates_statistics_for_single_earnings_event() -> None:
    price_analysis = make_price_analysis(
        report_date=date(2026, 4, 16),
        max_gain_percent=9.5,
        max_loss_percent=-4.5,
    )

    statistics = HistoricalPriceStatisticsAnalyzer().analyze(
        (price_analysis,)
    )

    assert statistics.earnings_count == 1
    assert statistics.average_max_gain_percent == pytest.approx(
        9.5
    )
    assert statistics.average_max_loss_percent == pytest.approx(
        -4.5
    )
    assert statistics.highest_max_gain_percent == pytest.approx(
        9.5
    )
    assert statistics.worst_max_loss_percent == pytest.approx(
        -4.5
    )
    assert statistics.median_max_gain_percent == pytest.approx(
        9.5
    )
    assert statistics.median_max_loss_percent == pytest.approx(
        -4.5
    )


def test_returns_empty_statistics_without_earnings() -> None:
    statistics = HistoricalPriceStatisticsAnalyzer().analyze(())

    assert statistics.earnings_count == 0
    assert statistics.average_max_gain_percent is None
    assert statistics.average_max_loss_percent is None
    assert statistics.highest_max_gain_percent is None
    assert statistics.worst_max_loss_percent is None
    assert statistics.median_max_gain_percent is None
    assert statistics.median_max_loss_percent is None