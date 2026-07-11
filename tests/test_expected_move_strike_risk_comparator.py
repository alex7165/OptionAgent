import pytest

from app.analysis.expected_move_strike_risk_comparator import (
    ExpectedMoveRiskAssessment,
    ExpectedMoveStrikeRiskComparator,
)
from app.analysis.historical_strike_risk_analyzer import (
    HistoricalStrikeRisk,
    StrikeSide,
)
from app.analysis.historical_strike_risk_grid_analyzer import (
    HistoricalStrikeRiskGrid,
)


def make_risk(
    *,
    side: StrikeSide,
    threshold_percent: float,
    finish_outside_probability: float,
    reached_probability: float,
    exit_trading_day_index: int = 2,
    observation_count: int = 20,
) -> HistoricalStrikeRisk:
    return HistoricalStrikeRisk(
        side=side,
        threshold_percent=threshold_percent,
        exit_trading_day_index=exit_trading_day_index,
        observation_count=observation_count,
        finish_inside_probability=(
            1.0 - finish_outside_probability
        ),
        finish_outside_probability=(
            finish_outside_probability
        ),
        reached_probability=reached_probability,
        worst_historical_move_percent=(
            20.0
            if side is StrikeSide.CALL
            else -20.0
        ),
    )


def make_grid() -> HistoricalStrikeRiskGrid:
    return HistoricalStrikeRiskGrid(
        call_risks=(
            make_risk(
                side=StrikeSide.CALL,
                threshold_percent=5.0,
                finish_outside_probability=0.30,
                reached_probability=0.55,
            ),
            make_risk(
                side=StrikeSide.CALL,
                threshold_percent=7.5,
                finish_outside_probability=0.15,
                reached_probability=0.35,
            ),
            make_risk(
                side=StrikeSide.CALL,
                threshold_percent=10.0,
                finish_outside_probability=0.10,
                reached_probability=0.20,
            ),
            make_risk(
                side=StrikeSide.CALL,
                threshold_percent=12.5,
                finish_outside_probability=0.05,
                reached_probability=0.10,
            ),
        ),
        put_risks=(
            make_risk(
                side=StrikeSide.PUT,
                threshold_percent=-5.0,
                finish_outside_probability=0.35,
                reached_probability=0.60,
            ),
            make_risk(
                side=StrikeSide.PUT,
                threshold_percent=-7.5,
                finish_outside_probability=0.20,
                reached_probability=0.40,
            ),
            make_risk(
                side=StrikeSide.PUT,
                threshold_percent=-10.0,
                finish_outside_probability=0.15,
                reached_probability=0.30,
            ),
            make_risk(
                side=StrikeSide.PUT,
                threshold_percent=-12.5,
                finish_outside_probability=0.05,
                reached_probability=0.15,
            ),
        ),
    )


def test_compares_expected_move_with_nearest_grid_risks() -> None:
    comparison = ExpectedMoveStrikeRiskComparator().compare(
        expected_move_percent=9.0,
        risk_grid=make_grid(),
        target_finish_outside_probability=0.10,
        neutral_tolerance=0.02,
    )

    assert comparison.expected_move_percent == 9.0

    call = comparison.call_comparison
    assert call is not None
    assert call.side is StrikeSide.CALL
    assert (
        call.expected_move_threshold_percent
        == pytest.approx(9.0)
    )
    assert (
        call.matched_risk.threshold_percent
        == pytest.approx(10.0)
    )
    assert (
        call.threshold_difference_percent
        == pytest.approx(1.0)
    )
    assert (
        call.next_outward_risk is not None
    )
    assert (
        call.next_outward_risk.threshold_percent
        == pytest.approx(12.5)
    )
    assert (
        call.finish_outside_probability_difference
        == pytest.approx(-0.05)
    )
    assert (
        call.reached_probability_difference
        == pytest.approx(-0.10)
    )
    assert (
        call.assessment
        is ExpectedMoveRiskAssessment.NEUTRAL
    )

    put = comparison.put_comparison
    assert put is not None
    assert put.side is StrikeSide.PUT
    assert (
        put.expected_move_threshold_percent
        == pytest.approx(-9.0)
    )
    assert (
        put.matched_risk.threshold_percent
        == pytest.approx(-10.0)
    )
    assert (
        put.threshold_difference_percent
        == pytest.approx(-1.0)
    )
    assert put.next_outward_risk is not None
    assert (
        put.next_outward_risk.threshold_percent
        == pytest.approx(-12.5)
    )
    assert (
        put.finish_outside_probability_difference
        == pytest.approx(-0.10)
    )
    assert (
        put.reached_probability_difference
        == pytest.approx(-0.15)
    )
    assert (
        put.assessment
        is ExpectedMoveRiskAssessment.TIGHT
    )


def test_marks_low_historical_risk_as_wide() -> None:
    grid = HistoricalStrikeRiskGrid(
        call_risks=(
            make_risk(
                side=StrikeSide.CALL,
                threshold_percent=10.0,
                finish_outside_probability=0.03,
                reached_probability=0.10,
            ),
        ),
        put_risks=(),
    )

    comparison = ExpectedMoveStrikeRiskComparator().compare(
        expected_move_percent=10.0,
        risk_grid=grid,
        target_finish_outside_probability=0.10,
        neutral_tolerance=0.02,
    )

    assert comparison.call_comparison is not None
    assert (
        comparison.call_comparison.assessment
        is ExpectedMoveRiskAssessment.WIDE
    )


def test_uses_nearer_threshold_when_expected_move_is_between_grid_points() -> None:
    comparison = ExpectedMoveStrikeRiskComparator().compare(
        expected_move_percent=8.0,
        risk_grid=make_grid(),
        target_finish_outside_probability=0.10,
    )

    assert comparison.call_comparison is not None
    assert (
        comparison.call_comparison
        .matched_risk
        .threshold_percent
        == pytest.approx(7.5)
    )

    assert comparison.put_comparison is not None
    assert (
        comparison.put_comparison
        .matched_risk
        .threshold_percent
        == pytest.approx(-7.5)
    )


def test_prefers_threshold_closer_to_reference_on_equal_distance() -> None:
    comparison = ExpectedMoveStrikeRiskComparator().compare(
        expected_move_percent=8.75,
        risk_grid=make_grid(),
        target_finish_outside_probability=0.10,
    )

    assert comparison.call_comparison is not None
    assert (
        comparison.call_comparison
        .matched_risk
        .threshold_percent
        == pytest.approx(7.5)
    )

    assert comparison.put_comparison is not None
    assert (
        comparison.put_comparison
        .matched_risk
        .threshold_percent
        == pytest.approx(-7.5)
    )


def test_returns_no_outward_comparison_at_outermost_threshold() -> None:
    comparison = ExpectedMoveStrikeRiskComparator().compare(
        expected_move_percent=12.5,
        risk_grid=make_grid(),
        target_finish_outside_probability=0.10,
    )

    assert comparison.call_comparison is not None
    assert (
        comparison.call_comparison.next_outward_risk
        is None
    )
    assert (
        comparison.call_comparison
        .finish_outside_probability_difference
        is None
    )
    assert (
        comparison.call_comparison
        .reached_probability_difference
        is None
    )

    assert comparison.put_comparison is not None
    assert (
        comparison.put_comparison.next_outward_risk
        is None
    )


def test_allows_one_sided_grid() -> None:
    grid = HistoricalStrikeRiskGrid(
        call_risks=make_grid().call_risks,
        put_risks=(),
    )

    comparison = ExpectedMoveStrikeRiskComparator().compare(
        expected_move_percent=10.0,
        risk_grid=grid,
        target_finish_outside_probability=0.10,
    )

    assert comparison.call_comparison is not None
    assert comparison.put_comparison is None


@pytest.mark.parametrize(
    "expected_move_percent",
    (
        0.0,
        -5.0,
    ),
)
def test_rejects_non_positive_expected_move(
    expected_move_percent: float,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "expected_move_percent must be greater than zero"
        ),
    ):
        ExpectedMoveStrikeRiskComparator().compare(
            expected_move_percent=expected_move_percent,
            risk_grid=make_grid(),
            target_finish_outside_probability=0.10,
        )


@pytest.mark.parametrize(
    "target_probability",
    (
        -0.01,
        1.01,
    ),
)
def test_rejects_invalid_target_probability(
    target_probability: float,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "target_finish_outside_probability must be "
            "between 0 and 1"
        ),
    ):
        ExpectedMoveStrikeRiskComparator().compare(
            expected_move_percent=10.0,
            risk_grid=make_grid(),
            target_finish_outside_probability=(
                target_probability
            ),
        )


def test_rejects_negative_neutral_tolerance() -> None:
    with pytest.raises(
        ValueError,
        match="neutral_tolerance must not be negative",
    ):
        ExpectedMoveStrikeRiskComparator().compare(
            expected_move_percent=10.0,
            risk_grid=make_grid(),
            target_finish_outside_probability=0.10,
            neutral_tolerance=-0.01,
        )


def test_rejects_inconsistent_risk_side() -> None:
    invalid_grid = HistoricalStrikeRiskGrid(
        call_risks=(
            make_risk(
                side=StrikeSide.PUT,
                threshold_percent=-10.0,
                finish_outside_probability=0.10,
                reached_probability=0.20,
            ),
        ),
        put_risks=(),
    )

    with pytest.raises(
        ValueError,
        match="call risks must all use call side",
    ):
        ExpectedMoveStrikeRiskComparator().compare(
            expected_move_percent=10.0,
            risk_grid=invalid_grid,
            target_finish_outside_probability=0.10,
        )