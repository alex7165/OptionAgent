from datetime import date

import pytest

from app.analysis.daily_move_analyzer import DailyMove
from app.analysis.historical_earnings_price_analyzer import (
    HistoricalEarningsPriceAnalysis,
)
from app.analysis.price_series_analyzer import (
    PriceSeriesAnalysis,
)
from app.analysis.trading_day_distribution_analyzer import (
    TradingDayDistributionAnalyzer,
)
from app.marketdata.earnings_api_provider import (
    HistoricalEarningsReaction,
)


def make_price_analysis(
    report_date: date,
    daily_moves: tuple[DailyMove, ...],
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
            highest_high=100.0,
            lowest_low=100.0,
            max_gain_percent=0.0,
            max_loss_percent=0.0,
        ),
        daily_moves=daily_moves,
    )


def make_daily_move(
    trading_day_index: int,
    move_date: date,
    open_percent: float,
    high_percent: float,
    low_percent: float,
    close_percent: float,
) -> DailyMove:
    return DailyMove(
        trading_day_index=trading_day_index,
        date=move_date,
        open_percent=open_percent,
        high_percent=high_percent,
        low_percent=low_percent,
        close_percent=close_percent,
    )


def test_calculates_distributions_for_each_trading_day() -> None:
    price_analyses = (
        make_price_analysis(
            report_date=date(2025, 10, 16),
            daily_moves=(
                make_daily_move(
                    trading_day_index=1,
                    move_date=date(2025, 10, 17),
                    open_percent=4.0,
                    high_percent=10.0,
                    low_percent=-2.0,
                    close_percent=6.0,
                ),
                make_daily_move(
                    trading_day_index=2,
                    move_date=date(2025, 10, 20),
                    open_percent=5.0,
                    high_percent=12.0,
                    low_percent=-4.0,
                    close_percent=8.0,
                ),
            ),
        ),
        make_price_analysis(
            report_date=date(2026, 1, 20),
            daily_moves=(
                make_daily_move(
                    trading_day_index=1,
                    move_date=date(2026, 1, 21),
                    open_percent=-6.0,
                    high_percent=2.0,
                    low_percent=-12.0,
                    close_percent=-8.0,
                ),
                make_daily_move(
                    trading_day_index=2,
                    move_date=date(2026, 1, 22),
                    open_percent=0.0,
                    high_percent=6.0,
                    low_percent=-10.0,
                    close_percent=-2.0,
                ),
            ),
        ),
    )

    distributions = TradingDayDistributionAnalyzer().analyze(
        price_analyses
    )

    assert len(distributions) == 2

    first_day = distributions[0]
    assert first_day.trading_day_index == 1
    assert first_day.observation_count == 2

    assert (
        first_day.open_distribution.average_percent
        == pytest.approx(-1.0)
    )
    assert (
        first_day.open_distribution.median_percent
        == pytest.approx(-1.0)
    )
    assert (
        first_day.open_distribution.minimum_percent
        == pytest.approx(-6.0)
    )
    assert (
        first_day.open_distribution.maximum_percent
        == pytest.approx(4.0)
    )
    assert (
        first_day.open_distribution.percentile_25
        == pytest.approx(-3.5)
    )
    assert (
        first_day.open_distribution.percentile_75
        == pytest.approx(1.5)
    )
    assert (
        first_day.open_distribution.positive_ratio
        == pytest.approx(0.5)
    )
    assert (
        first_day.open_distribution.negative_ratio
        == pytest.approx(0.5)
    )
    assert (
        first_day.open_distribution.unchanged_ratio
        == pytest.approx(0.0)
    )

    assert (
        first_day.high_distribution.average_percent
        == pytest.approx(6.0)
    )
    assert (
        first_day.low_distribution.average_percent
        == pytest.approx(-7.0)
    )
    assert (
        first_day.close_distribution.average_percent
        == pytest.approx(-1.0)
    )

    second_day = distributions[1]
    assert second_day.trading_day_index == 2
    assert second_day.observation_count == 2
    assert (
        second_day.close_distribution.minimum_percent
        == pytest.approx(-2.0)
    )
    assert (
        second_day.close_distribution.maximum_percent
        == pytest.approx(8.0)
    )


def test_uses_only_available_observations_for_each_day() -> None:
    price_analyses = (
        make_price_analysis(
            report_date=date(2025, 10, 16),
            daily_moves=(
                make_daily_move(
                    trading_day_index=1,
                    move_date=date(2025, 10, 17),
                    open_percent=2.0,
                    high_percent=5.0,
                    low_percent=-1.0,
                    close_percent=3.0,
                ),
                make_daily_move(
                    trading_day_index=2,
                    move_date=date(2025, 10, 20),
                    open_percent=3.0,
                    high_percent=7.0,
                    low_percent=-2.0,
                    close_percent=5.0,
                ),
            ),
        ),
        make_price_analysis(
            report_date=date(2026, 1, 20),
            daily_moves=(
                make_daily_move(
                    trading_day_index=1,
                    move_date=date(2026, 1, 21),
                    open_percent=-2.0,
                    high_percent=1.0,
                    low_percent=-6.0,
                    close_percent=-4.0,
                ),
            ),
        ),
    )

    distributions = TradingDayDistributionAnalyzer().analyze(
        price_analyses
    )

    assert distributions[0].observation_count == 2
    assert distributions[1].observation_count == 1

    second_day_close = (
        distributions[1].close_distribution
    )
    assert second_day_close.observation_count == 1
    assert second_day_close.average_percent == pytest.approx(
        5.0
    )
    assert second_day_close.percentile_25 == pytest.approx(
        5.0
    )
    assert second_day_close.percentile_75 == pytest.approx(
        5.0
    )


def test_calculates_positive_negative_and_unchanged_ratios() -> None:
    price_analyses = (
        make_price_analysis(
            report_date=date(2025, 7, 17),
            daily_moves=(
                make_daily_move(
                    trading_day_index=1,
                    move_date=date(2025, 7, 18),
                    open_percent=5.0,
                    high_percent=5.0,
                    low_percent=5.0,
                    close_percent=5.0,
                ),
            ),
        ),
        make_price_analysis(
            report_date=date(2025, 10, 16),
            daily_moves=(
                make_daily_move(
                    trading_day_index=1,
                    move_date=date(2025, 10, 17),
                    open_percent=-5.0,
                    high_percent=-5.0,
                    low_percent=-5.0,
                    close_percent=-5.0,
                ),
            ),
        ),
        make_price_analysis(
            report_date=date(2026, 1, 20),
            daily_moves=(
                make_daily_move(
                    trading_day_index=1,
                    move_date=date(2026, 1, 21),
                    open_percent=0.0,
                    high_percent=0.0,
                    low_percent=0.0,
                    close_percent=0.0,
                ),
            ),
        ),
    )

    distributions = TradingDayDistributionAnalyzer().analyze(
        price_analyses
    )

    close_distribution = (
        distributions[0].close_distribution
    )

    assert close_distribution.positive_ratio == pytest.approx(
        1 / 3
    )
    assert close_distribution.negative_ratio == pytest.approx(
        1 / 3
    )
    assert close_distribution.unchanged_ratio == pytest.approx(
        1 / 3
    )


def test_returns_empty_result_without_price_analyses() -> None:
    distributions = TradingDayDistributionAnalyzer().analyze(
        ()
    )

    assert distributions == ()


def test_returns_empty_result_when_analyses_have_no_daily_moves() -> None:
    price_analysis = make_price_analysis(
        report_date=date(2026, 4, 16),
        daily_moves=(),
    )

    distributions = TradingDayDistributionAnalyzer().analyze(
        (price_analysis,)
    )

    assert distributions == ()


def test_rejects_duplicate_day_index_within_one_event() -> None:
    price_analysis = make_price_analysis(
        report_date=date(2026, 4, 16),
        daily_moves=(
            make_daily_move(
                trading_day_index=1,
                move_date=date(2026, 4, 17),
                open_percent=2.0,
                high_percent=4.0,
                low_percent=-1.0,
                close_percent=3.0,
            ),
            make_daily_move(
                trading_day_index=1,
                move_date=date(2026, 4, 20),
                open_percent=3.0,
                high_percent=5.0,
                low_percent=-2.0,
                close_percent=4.0,
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "daily_moves must contain unique "
            "trading_day_index values per earnings event"
        ),
    ):
        TradingDayDistributionAnalyzer().analyze(
            (price_analysis,)
        )


def test_rejects_non_positive_day_index() -> None:
    price_analysis = make_price_analysis(
        report_date=date(2026, 4, 16),
        daily_moves=(
            make_daily_move(
                trading_day_index=0,
                move_date=date(2026, 4, 17),
                open_percent=2.0,
                high_percent=4.0,
                low_percent=-1.0,
                close_percent=3.0,
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="trading_day_index must be at least 1",
    ):
        TradingDayDistributionAnalyzer().analyze(
            (price_analysis,)
        )