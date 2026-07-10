from datetime import date

import pytest

from app.analysis.historical_outcome_analyzer import (
    HistoricalOutcome,
)
from app.analysis.historical_strike_risk_analyzer import (
    HistoricalStrikeRiskAnalyzer,
    StrikeSide,
)
from app.analysis.historical_strike_risk_grid_analyzer import (
    HistoricalStrikeRiskGridAnalyzer,
)


def make_outcome(
    *,
    exit_close_percent: float,
    highest_percent_until_exit: float,
    lowest_percent_until_exit: float,
    exit_trading_day_index: int = 2,
) -> HistoricalOutcome:
    return HistoricalOutcome(
        exit_trading_day_index=exit_trading_day_index,
        exit_date=date(2026, 4, 20),
        exit_close_percent=exit_close_percent,
        highest_percent_until_exit=(
            highest_percent_until_exit
        ),
        lowest_percent_until_exit=(
            lowest_percent_until_exit
        ),
        trading_days_observed=exit_trading_day_index,
    )


def make_analyzer() -> HistoricalStrikeRiskGridAnalyzer:
    return HistoricalStrikeRiskGridAnalyzer(
        strike_risk_analyzer=(
            HistoricalStrikeRiskAnalyzer()
        ),
    )


def make_outcomes() -> tuple[HistoricalOutcome, ...]:
    return (
        make_outcome(
            exit_close_percent=12.0,
            highest_percent_until_exit=15.0,
            lowest_percent_until_exit=-4.0,
        ),
        make_outcome(
            exit_close_percent=7.0,
            highest_percent_until_exit=11.0,
            lowest_percent_until_exit=-8.0,
        ),
        make_outcome(
            exit_close_percent=-6.0,
            highest_percent_until_exit=4.0,
            lowest_percent_until_exit=-13.0,
        ),
        make_outcome(
            exit_close_percent=-11.0,
            highest_percent_until_exit=2.0,
            lowest_percent_until_exit=-16.0,
        ),
    )


def test_calculates_call_and_put_risk_grid() -> None:
    grid = make_analyzer().analyze(
        outcomes=make_outcomes(),
        call_thresholds=(
            5.0,
            10.0,
            15.0,
        ),
        put_thresholds=(
            -5.0,
            -10.0,
            -15.0,
        ),
    )

    assert len(grid.call_risks) == 3
    assert len(grid.put_risks) == 3

    call_10 = grid.call_risks[1]

    assert call_10.side is StrikeSide.CALL
    assert call_10.threshold_percent == 10.0
    assert call_10.observation_count == 4
    assert (
        call_10.finish_outside_probability
        == pytest.approx(0.25)
    )
    assert (
        call_10.reached_probability
        == pytest.approx(0.5)
    )

    put_10 = grid.put_risks[1]

    assert put_10.side is StrikeSide.PUT
    assert put_10.threshold_percent == -10.0
    assert put_10.observation_count == 4
    assert (
        put_10.finish_outside_probability
        == pytest.approx(0.25)
    )
    assert (
        put_10.reached_probability
        == pytest.approx(0.5)
    )


def test_orders_thresholds_by_distance_from_reference_price() -> None:
    grid = make_analyzer().analyze(
        outcomes=make_outcomes(),
        call_thresholds=(
            15.0,
            5.0,
            10.0,
            7.5,
        ),
        put_thresholds=(
            -15.0,
            -5.0,
            -10.0,
            -7.5,
        ),
    )

    assert tuple(
        risk.threshold_percent
        for risk in grid.call_risks
    ) == (
        5.0,
        7.5,
        10.0,
        15.0,
    )

    assert tuple(
        risk.threshold_percent
        for risk in grid.put_risks
    ) == (
        -5.0,
        -7.5,
        -10.0,
        -15.0,
    )


def test_all_risks_use_same_exit_day_and_observation_count() -> None:
    grid = make_analyzer().analyze(
        outcomes=make_outcomes(),
        call_thresholds=(
            5.0,
            10.0,
        ),
        put_thresholds=(
            -5.0,
            -10.0,
        ),
    )

    all_risks = (
        grid.call_risks
        + grid.put_risks
    )

    assert {
        risk.exit_trading_day_index
        for risk in all_risks
    } == {
        2,
    }

    assert {
        risk.observation_count
        for risk in all_risks
    } == {
        4,
    }


def test_allows_call_only_grid() -> None:
    grid = make_analyzer().analyze(
        outcomes=make_outcomes(),
        call_thresholds=(
            5.0,
            10.0,
        ),
        put_thresholds=(),
    )

    assert len(grid.call_risks) == 2
    assert grid.put_risks == ()


def test_allows_put_only_grid() -> None:
    grid = make_analyzer().analyze(
        outcomes=make_outcomes(),
        call_thresholds=(),
        put_thresholds=(
            -5.0,
            -10.0,
        ),
    )

    assert grid.call_risks == ()
    assert len(grid.put_risks) == 2


def test_returns_empty_grid_when_no_thresholds_are_requested() -> None:
    grid = make_analyzer().analyze(
        outcomes=make_outcomes(),
        call_thresholds=(),
        put_thresholds=(),
    )

    assert grid.call_risks == ()
    assert grid.put_risks == ()


def test_rejects_empty_outcomes() -> None:
    with pytest.raises(
        ValueError,
        match="outcomes must not be empty",
    ):
        make_analyzer().analyze(
            outcomes=(),
            call_thresholds=(10.0,),
            put_thresholds=(-10.0,),
        )


def test_rejects_duplicate_call_thresholds() -> None:
    with pytest.raises(
        ValueError,
        match="call thresholds must be unique",
    ):
        make_analyzer().analyze(
            outcomes=make_outcomes(),
            call_thresholds=(
                10.0,
                5.0,
                10.0,
            ),
            put_thresholds=(-10.0,),
        )


def test_rejects_duplicate_put_thresholds() -> None:
    with pytest.raises(
        ValueError,
        match="put thresholds must be unique",
    ):
        make_analyzer().analyze(
            outcomes=make_outcomes(),
            call_thresholds=(10.0,),
            put_thresholds=(
                -10.0,
                -5.0,
                -10.0,
            ),
        )


def test_rejects_invalid_call_threshold_through_risk_analyzer() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Call threshold_percent must be "
            "greater than zero"
        ),
    ):
        make_analyzer().analyze(
            outcomes=make_outcomes(),
            call_thresholds=(
                0.0,
                10.0,
            ),
            put_thresholds=(-10.0,),
        )


def test_rejects_invalid_put_threshold_through_risk_analyzer() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Put threshold_percent must be "
            "less than zero"
        ),
    ):
        make_analyzer().analyze(
            outcomes=make_outcomes(),
            call_thresholds=(10.0,),
            put_thresholds=(
                0.0,
                -10.0,
            ),
        )