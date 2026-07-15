from datetime import date

import pytest

from app.analysis.daily_move_analyzer import DailyMove
from app.analysis.historical_earnings_price_analyzer import (
    HistoricalEarningsPriceAnalysis,
)
from app.analysis.historical_outcome_analyzer import (
    HistoricalOutcomeAnalyzer,
)
from app.analysis.historical_strike_risk_analyzer import (
    HistoricalStrikeRiskAnalyzer,
)
from app.analysis.historical_strike_risk_grid_analyzer import (
    HistoricalStrikeRiskGridAnalyzer,
)
from app.analysis.historical_strike_selection_service import (
    HistoricalStrikeSelectionService,
)
from app.analysis.historical_strike_selector import (
    HistoricalStrikeSelectionPolicy,
    HistoricalStrikeSelectionReason,
    HistoricalStrikeSelector,
)
from app.analysis.price_series_analyzer import (
    PriceSeriesAnalysis,
)
from app.marketdata.earnings_api_provider import (
    HistoricalEarningsReaction,
)


def make_price_analysis(
    *,
    report_date: date,
    first_date: date,
    first_high_percent: float,
    first_low_percent: float,
    first_close_percent: float,
    second_high_percent: float,
    second_low_percent: float,
    second_close_percent: float,
) -> HistoricalEarningsPriceAnalysis:
    second_date = date.fromordinal(
        first_date.toordinal() + 1
    )

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
            first_date=first_date,
            last_date=second_date,
            first_open=100.0,
            first_close=(
                100.0 + first_close_percent
            ),
            last_close=(
                100.0 + second_close_percent
            ),
            highest_high=(
                100.0
                + max(
                    first_high_percent,
                    second_high_percent,
                )
            ),
            lowest_low=(
                100.0
                + min(
                    first_low_percent,
                    second_low_percent,
                )
            ),
            max_gain_percent=max(
                first_high_percent,
                second_high_percent,
            ),
            max_loss_percent=min(
                first_low_percent,
                second_low_percent,
            ),
        ),
        daily_moves=(
            DailyMove(
                trading_day_index=1,
                date=first_date,
                open_percent=0.0,
                high_percent=first_high_percent,
                low_percent=first_low_percent,
                close_percent=first_close_percent,
            ),
            DailyMove(
                trading_day_index=2,
                date=second_date,
                open_percent=first_close_percent,
                high_percent=second_high_percent,
                low_percent=second_low_percent,
                close_percent=second_close_percent,
            ),
        ),
    )


def make_price_analyses() -> tuple[
    HistoricalEarningsPriceAnalysis,
    ...,
]:
    return (
        make_price_analysis(
            report_date=date(2025, 7, 17),
            first_date=date(2025, 7, 18),
            first_high_percent=8.0,
            first_low_percent=-4.0,
            first_close_percent=5.0,
            second_high_percent=12.0,
            second_low_percent=-6.0,
            second_close_percent=10.0,
        ),
        make_price_analysis(
            report_date=date(2025, 10, 16),
            first_date=date(2025, 10, 17),
            first_high_percent=5.0,
            first_low_percent=-8.0,
            first_close_percent=-4.0,
            second_high_percent=7.0,
            second_low_percent=-12.0,
            second_close_percent=-9.0,
        ),
        make_price_analysis(
            report_date=date(2026, 1, 20),
            first_date=date(2026, 1, 21),
            first_high_percent=4.0,
            first_low_percent=-3.0,
            first_close_percent=2.0,
            second_high_percent=6.0,
            second_low_percent=-5.0,
            second_close_percent=3.0,
        ),
        make_price_analysis(
            report_date=date(2026, 4, 16),
            first_date=date(2026, 4, 17),
            first_high_percent=10.0,
            first_low_percent=-5.0,
            first_close_percent=7.0,
            second_high_percent=15.0,
            second_low_percent=-7.0,
            second_close_percent=12.0,
        ),
    )


def make_service() -> HistoricalStrikeSelectionService:
    return HistoricalStrikeSelectionService(
        outcome_analyzer=HistoricalOutcomeAnalyzer(),
        risk_grid_analyzer=(
            HistoricalStrikeRiskGridAnalyzer(
                strike_risk_analyzer=(
                    HistoricalStrikeRiskAnalyzer()
                ),
            )
        ),
        strike_selector=HistoricalStrikeSelector(),
    )


def test_runs_complete_historical_strike_selection_workflow() -> None:
    result = make_service().select(
        price_analyses=make_price_analyses(),
        expected_move_percent=9.0,
        exit_trading_day_index=2,
        call_thresholds=(
            7.5,
            10.0,
            12.5,
            15.0,
        ),
        put_thresholds=(
            -7.5,
            -10.0,
            -12.5,
            -15.0,
        ),
        policy=HistoricalStrikeSelectionPolicy(
            max_finish_outside_probability=0.25,
            max_reached_probability=0.50,
        ),
    )

    assert len(result.outcomes) == 4

    assert {
        outcome.exit_trading_day_index
        for outcome in result.outcomes
    } == {
        2,
    }

    assert tuple(
        risk.threshold_percent
        for risk in result.risk_grid.call_risks
    ) == (
        7.5,
        10.0,
        12.5,
        15.0,
    )

    assert tuple(
        risk.threshold_percent
        for risk in result.risk_grid.put_risks
    ) == (
        -7.5,
        -10.0,
        -12.5,
        -15.0,
    )

    call = result.selection.call_recommendation
    assert call is not None
    assert (
        call.recommended_threshold_percent
        == pytest.approx(10.0)
    )
    assert (
        call.finish_outside_probability
        == pytest.approx(0.25)
    )
    assert (
        call.reached_probability
        == pytest.approx(0.50)
    )
    assert (
        call.reason
        is HistoricalStrikeSelectionReason.ADJUSTED_OUTWARD
    )

    put = result.selection.put_recommendation
    assert put is not None
    assert (
        put.recommended_threshold_percent
        == pytest.approx(-10.0)
    )
    assert (
        put.finish_outside_probability
        == pytest.approx(0.0)
    )
    assert (
        put.reached_probability
        == pytest.approx(0.25)
    )
    assert (
        put.reason
        is HistoricalStrikeSelectionReason.ADJUSTED_OUTWARD
    )


def test_uses_only_moves_up_to_selected_exit_day() -> None:
    result = make_service().select(
        price_analyses=make_price_analyses(),
        expected_move_percent=7.0,
        exit_trading_day_index=1,
        call_thresholds=(
            5.0,
            7.5,
            10.0,
        ),
        put_thresholds=(
            -5.0,
            -7.5,
            -10.0,
        ),
        policy=HistoricalStrikeSelectionPolicy(
            max_finish_outside_probability=0.50,
            max_reached_probability=0.75,
        ),
    )

    assert all(
        outcome.trading_days_observed == 1
        for outcome in result.outcomes
    )

    call_10 = next(
        risk
        for risk in result.risk_grid.call_risks
        if risk.threshold_percent == 10.0
    )

    assert call_10.reached_probability == pytest.approx(
        0.25
    )


def test_returns_no_recommendation_when_policy_is_not_met() -> None:
    result = make_service().select(
        price_analyses=make_price_analyses(),
        expected_move_percent=9.0,
        exit_trading_day_index=2,
        call_thresholds=(
            7.5,
            10.0,
        ),
        put_thresholds=(
            -7.5,
            -10.0,
        ),
        policy=HistoricalStrikeSelectionPolicy(
            max_finish_outside_probability=0.0,
            max_reached_probability=0.0,
        ),
    )

    assert result.selection.call_recommendation is None
    assert result.selection.put_recommendation is None


def test_supports_one_sided_threshold_grid() -> None:
    result = make_service().select(
        price_analyses=make_price_analyses(),
        expected_move_percent=9.0,
        exit_trading_day_index=2,
        call_thresholds=(
            10.0,
            12.5,
        ),
        put_thresholds=(),
        policy=HistoricalStrikeSelectionPolicy(
            max_finish_outside_probability=0.25,
            max_reached_probability=0.50,
        ),
    )

    assert result.selection.call_recommendation is not None
    assert result.selection.put_recommendation is None
    assert result.risk_grid.put_risks == ()


def test_rejects_empty_price_analyses() -> None:
    with pytest.raises(
        ValueError,
        match="price_analyses must not be empty",
    ):
        make_service().select(
            price_analyses=(),
            expected_move_percent=9.0,
            exit_trading_day_index=2,
            call_thresholds=(10.0,),
            put_thresholds=(-10.0,),
            policy=HistoricalStrikeSelectionPolicy(
                max_finish_outside_probability=0.10,
            ),
        )


def test_rejects_when_an_event_has_no_selected_exit_day() -> None:
    price_analysis = make_price_analyses()[0]

    with pytest.raises(
        ValueError,
        match="No daily move found for exit trading day 3",
    ):
        make_service().select(
            price_analyses=(price_analysis,),
            expected_move_percent=9.0,
            exit_trading_day_index=3,
            call_thresholds=(10.0,),
            put_thresholds=(-10.0,),
            policy=HistoricalStrikeSelectionPolicy(
                max_finish_outside_probability=0.25,
            ),
        )


def test_select_best_exit_chooses_smallest_expected_move_adjustment() -> None:
    result = make_service().select_best_exit(
        price_analyses=make_price_analyses(),
        expected_move_percent=9.0,
        call_thresholds=(10.0, 12.5, 15.0),
        put_thresholds=(-10.0, -12.5, -15.0),
        policy=HistoricalStrikeSelectionPolicy(
            max_finish_outside_probability=0.25,
            max_reached_probability=0.50,
        ),
    )

    assert result.selection.call_recommendation is not None
    assert result.selection.put_recommendation is not None
    assert (
        result.selection.call_recommendation.exit_trading_day_index
        == 1
    )
    assert (
        result.selection.put_recommendation.exit_trading_day_index
        == 1
    )
