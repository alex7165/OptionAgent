from datetime import date

import pytest

from app.analysis.backtest_outcome_analyzer import BacktestOutcome
from app.analysis.decision_report import DecisionReport
from app.analysis.failure_attribution import (
    FailureAttributionAnalyzer,
    FailureCause,
    FailureSeverity,
)
from app.analysis.historical_strike_risk_analyzer import StrikeSide
from app.analysis.strategy_selector import StrikeSelectionSource
from app.analysis.trade_score import TradeScore


def score() -> TradeScore:
    return TradeScore(
        total=80.0,
        market_component=30.0,
        historical_risk_component=20.0,
        historical_sample_component=8.0,
        liquidity_component=22.0,
    )


def report(
    *,
    put_basis: str = "Expected Move",
    call_basis: str = "Expected Move",
    historical_put: float | None = -7.0,
    historical_call: float | None = 7.0,
    historical_max: float | None = 10.0,
) -> DecisionReport:
    return DecisionReport(
        selection_source=StrikeSelectionSource.HISTORICAL,
        expected_move_percent=6.0,
        historical_sample_size=30,
        exit_trading_day_index=2,
        historical_average_abs_close_move_percent=4.0,
        historical_median_abs_close_move_percent=3.5,
        historical_max_abs_close_move_percent=historical_max,
        historical_put_target_percent=historical_put,
        historical_call_target_percent=historical_call,
        used_put_target_percent=-7.0,
        used_call_target_percent=7.0,
        put_target_basis=put_basis,
        call_target_basis=call_basis,
        put_finish_outside_probability=0.05,
        call_finish_outside_probability=0.05,
        put_reached_probability=0.10,
        call_reached_probability=0.10,
        average_low_percent_until_exit=-3.0,
        average_high_percent_until_exit=3.0,
        initial_put_strike=93.0,
        initial_call_strike=107.0,
        final_put_strike=92.0,
        final_call_strike=108.0,
        liquidity_optimization_reason=None,
        trade_score=score(),
    )


def outcome(
    *,
    put_touched: bool = False,
    call_touched: bool = False,
    put_outside: bool = False,
    call_outside: bool = False,
    adverse: float = -3.0,
    favorable: float = 3.0,
) -> BacktestOutcome:
    return BacktestOutcome(
        exit_trading_day_index=2,
        exit_date=date(2026, 7, 15),
        exit_close=100.0,
        short_put_strike=92.0,
        short_call_strike=108.0,
        put_touched=put_touched,
        call_touched=call_touched,
        put_finished_outside=put_outside,
        call_finished_outside=call_outside,
        finished_inside_short_strikes=not put_outside and not call_outside,
        max_adverse_move_percent=adverse,
        max_favorable_move_percent=favorable,
        holding_days=2,
    )


def test_reports_no_failure_without_touch_or_violation() -> None:
    result = FailureAttributionAnalyzer().analyze(
        report=report(),
        outcome=outcome(),
        reference_price=100.0,
    )

    assert result.severity is FailureSeverity.NONE
    assert result.primary_cause is FailureCause.NONE
    assert result.affected_sides == ()


def test_attributes_inside_exit_with_touch_to_path_risk() -> None:
    result = FailureAttributionAnalyzer().analyze(
        report=report(),
        outcome=outcome(call_touched=True, favorable=8.5),
        reference_price=100.0,
    )

    assert result.severity is FailureSeverity.CRITICAL
    assert result.primary_cause is FailureCause.EXIT_PATH_RISK
    assert result.affected_sides[0].side is StrikeSide.CALL


def test_attributes_expected_move_based_failure_to_current_market() -> None:
    result = FailureAttributionAnalyzer().analyze(
        report=report(call_basis="Expected Move", historical_max=None),
        outcome=outcome(
            call_touched=True,
            call_outside=True,
            favorable=9.0,
        ),
        reference_price=100.0,
    )

    assert result.severity is FailureSeverity.FAILURE
    assert result.primary_cause is FailureCause.CURRENT_MARKET_UNDERESTIMATED


def test_attributes_history_based_failure_to_historical_target() -> None:
    result = FailureAttributionAnalyzer().analyze(
        report=report(
            call_basis="Historie",
            historical_call=7.0,
            historical_max=None,
        ),
        outcome=outcome(
            call_touched=True,
            call_outside=True,
            favorable=9.0,
        ),
        reference_price=100.0,
    )

    assert result.primary_cause is FailureCause.HISTORICAL_TARGET_UNDERESTIMATED


def test_flags_possible_outlier_beyond_market_and_historical_maximum() -> None:
    result = FailureAttributionAnalyzer().analyze(
        report=report(historical_max=10.0),
        outcome=outcome(
            put_touched=True,
            put_outside=True,
            adverse=-13.0,
        ),
        reference_price=100.0,
    )

    assert result.primary_cause is FailureCause.POSSIBLE_EXTREME_OUTLIER
    assert result.affected_sides[0].distance_shortfall_percent == 5.0
    assert any("vorsichtig" in text for text in result.observations)


def test_reports_both_affected_sides() -> None:
    result = FailureAttributionAnalyzer().analyze(
        report=report(historical_max=None),
        outcome=outcome(
            put_touched=True,
            call_touched=True,
            put_outside=True,
            adverse=-9.0,
            favorable=8.5,
        ),
        reference_price=100.0,
    )

    assert tuple(side.side for side in result.affected_sides) == (
        StrikeSide.PUT,
        StrikeSide.CALL,
    )


def test_rejects_invalid_reference_price() -> None:
    with pytest.raises(
        ValueError,
        match="reference_price must be greater than zero",
    ):
        FailureAttributionAnalyzer().analyze(
            report=report(),
            outcome=outcome(),
            reference_price=0.0,
        )
