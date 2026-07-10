from datetime import date

import pytest

from app.analysis.historical_earnings_analysis import (
    HistoricalEarningsAnalysis,
    HistoricalEarningsPriceSeries,
)
from app.analysis.historical_earnings_analysis_analyzer import (
    HistoricalEarningsAnalysisAnalyzer,
)
from app.analysis.historical_earnings_price_analyzer import (
    HistoricalEarningsPriceAnalyzer,
)
from app.analysis.price_series_analyzer import PriceSeriesAnalyzer
from app.marketdata.earnings_api_provider import (
    HistoricalEarningsReaction,
)
from app.marketdata.price_history_provider import DailyBar


def make_earnings_reaction(
    report_date: date,
) -> HistoricalEarningsReaction:
    return HistoricalEarningsReaction(
        report_date=report_date,
        symbol="NFLX",
        eps_surprise_percent=5.0,
        eps_yoy_percent=10.0,
        eps_beat=True,
        revenue_surprise_percent=2.0,
        revenue_yoy_percent=8.0,
        revenue_beat=True,
        reactions=(),
    )


def make_price_series(
    report_date: date,
    first_trading_date: date,
    high: float,
    low: float,
) -> HistoricalEarningsPriceSeries:
    return HistoricalEarningsPriceSeries(
        earnings=make_earnings_reaction(report_date),
        daily_bars=(
            DailyBar(
                date=first_trading_date,
                open=100.0,
                high=high,
                low=low,
                close=102.0,
                volume=1_000_000,
            ),
        ),
    )


def make_analyzer() -> HistoricalEarningsAnalysisAnalyzer:
    return HistoricalEarningsAnalysisAnalyzer(
        price_analyzer=HistoricalEarningsPriceAnalyzer(
            price_series_analyzer=PriceSeriesAnalyzer(),
        ),
    )


def test_analyzes_all_historical_earnings_price_series() -> None:
    first_series = make_price_series(
        report_date=date(2025, 10, 16),
        first_trading_date=date(2025, 10, 17),
        high=110.0,
        low=90.0,
    )
    second_series = make_price_series(
        report_date=date(2026, 1, 20),
        first_trading_date=date(2026, 1, 21),
        high=120.0,
        low=96.0,
    )

    reference_prices = {
        date(2025, 10, 16): 100.0,
        date(2026, 1, 20): 80.0,
    }

    result = make_analyzer().analyze(
        analysis=HistoricalEarningsAnalysis(
            price_series=(
                first_series,
                second_series,
            ),
        ),
        reference_price_resolver=lambda series: reference_prices[
            series.earnings.report_date
        ],
    )

    assert len(result.price_analyses) == 2

    first_analysis = result.price_analyses[0]
    assert first_analysis.earnings is first_series.earnings
    assert first_analysis.price_analysis.reference_price == 100.0
    assert first_analysis.price_analysis.max_gain_percent == pytest.approx(
        10.0
    )
    assert first_analysis.price_analysis.max_loss_percent == pytest.approx(
        -10.0
    )

    second_analysis = result.price_analyses[1]
    assert second_analysis.earnings is second_series.earnings
    assert second_analysis.price_analysis.reference_price == 80.0
    assert second_analysis.price_analysis.max_gain_percent == pytest.approx(
        50.0
    )
    assert second_analysis.price_analysis.max_loss_percent == pytest.approx(
        20.0
    )


def test_preserves_price_series_order() -> None:
    first_series = make_price_series(
        report_date=date(2025, 7, 17),
        first_trading_date=date(2025, 7, 18),
        high=105.0,
        low=95.0,
    )
    second_series = make_price_series(
        report_date=date(2025, 10, 16),
        first_trading_date=date(2025, 10, 17),
        high=108.0,
        low=92.0,
    )

    result = make_analyzer().analyze(
        analysis=HistoricalEarningsAnalysis(
            price_series=(
                first_series,
                second_series,
            ),
        ),
        reference_price_resolver=lambda series: 100.0,
    )

    assert tuple(
        item.earnings.report_date
        for item in result.price_analyses
    ) == (
        date(2025, 7, 17),
        date(2025, 10, 16),
    )


def test_returns_empty_result_when_no_price_series_exist() -> None:
    result = make_analyzer().analyze(
        analysis=HistoricalEarningsAnalysis(),
        reference_price_resolver=lambda series: 100.0,
    )

    assert result.price_analyses == ()