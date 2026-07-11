import pytest

from app.analysis.historical_strike_risk_analyzer import (
    HistoricalStrikeRisk,
    StrikeSide,
)
from app.analysis.historical_strike_risk_grid_analyzer import (
    HistoricalStrikeRiskGrid,
)
from app.analysis.historical_strike_selector import (
    HistoricalStrikeSelectionPolicy,
    HistoricalStrikeSelectionReason,
    HistoricalStrikeSelector,
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
                finish_outside_probability=0.08,
                reached_probability=0.20,
            ),
            make_risk(
                side=StrikeSide.CALL,
                threshold_percent=12.5,
                finish_outside_probability=0.04,
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
                finish_outside_probability=0.18,
                reached_probability=0.40,
            ),
            make_risk(
                side=StrikeSide.PUT,
                threshold_percent=-10.0,
                finish_outside_probability=0.12,
                reached_probability=0.28,
            ),
            make_risk(
                side=StrikeSide.PUT,
                threshold_percent=-12.5,
                finish_outside_probability=0.05,
                reached_probability=0.15,
            ),
        ),
    )


def test_selects_nearest_acceptable_strikes_to_expected_move() -> None:
    selection = HistoricalStrikeSelector().select(
        risk_grid=make_grid(),
        expected_move_percent=9.0,
        policy=HistoricalStrikeSelectionPolicy(
            max_finish_outside_probability=0.10,
            max_reached_probability=0.25,
        ),
    )

    call = selection.call_recommendation
    assert call is not None
    assert call.side is StrikeSide.CALL
    assert (
        call.recommended_threshold_percent
        == pytest.approx(10.0)
    )
    assert (
        call.expected_move_threshold_percent
        == pytest.approx(9.0)
    )
    assert (
        call.adjustment_from_expected_move
        == pytest.approx(1.0)
    )
    assert call.finish_outside_probability == pytest.approx(
        0.08
    )
    assert call.reached_probability == pytest.approx(
        0.20
    )
    assert (
        call.reason
        is HistoricalStrikeSelectionReason.ADJUSTED_OUTWARD
    )

    put = selection.put_recommendation
    assert put is not None
    assert put.side is StrikeSide.PUT
    assert (
        put.recommended_threshold_percent
        == pytest.approx(-12.5)
    )
    assert (
        put.expected_move_threshold_percent
        == pytest.approx(-9.0)
    )
    assert (
        put.adjustment_from_expected_move
        == pytest.approx(-3.5)
    )
    assert put.finish_outside_probability == pytest.approx(
        0.05
    )
    assert put.reached_probability == pytest.approx(
        0.15
    )
    assert (
        put.reason
        is HistoricalStrikeSelectionReason.ADJUSTED_OUTWARD
    )


def test_can_adjust_inward_when_risk_limits_are_met() -> None:
    selection = HistoricalStrikeSelector().select(
        risk_grid=make_grid(),
        expected_move_percent=11.0,
        policy=HistoricalStrikeSelectionPolicy(
            max_finish_outside_probability=0.10,
            max_reached_probability=0.25,
            allow_inward_adjustment=True,
        ),
    )

    call = selection.call_recommendation
    assert call is not None
    assert (
        call.recommended_threshold_percent
        == pytest.approx(10.0)
    )
    assert (
        call.reason
        is HistoricalStrikeSelectionReason.ADJUSTED_INWARD
    )

    put = selection.put_recommendation
    assert put is not None
    assert (
        put.recommended_threshold_percent
        == pytest.approx(-12.5)
    )
    assert (
        put.reason
        is HistoricalStrikeSelectionReason.ADJUSTED_OUTWARD
    )


def test_can_forbid_inward_adjustment() -> None:
    selection = HistoricalStrikeSelector().select(
        risk_grid=make_grid(),
        expected_move_percent=11.0,
        policy=HistoricalStrikeSelectionPolicy(
            max_finish_outside_probability=0.10,
            max_reached_probability=0.25,
            allow_inward_adjustment=False,
        ),
    )

    call = selection.call_recommendation
    assert call is not None
    assert (
        call.recommended_threshold_percent
        == pytest.approx(12.5)
    )
    assert (
        call.reason
        is HistoricalStrikeSelectionReason.ADJUSTED_OUTWARD
    )

    put = selection.put_recommendation
    assert put is not None
    assert (
        put.recommended_threshold_percent
        == pytest.approx(-12.5)
    )


def test_marks_exact_expected_move_match() -> None:
    selection = HistoricalStrikeSelector().select(
        risk_grid=make_grid(),
        expected_move_percent=10.0,
        policy=HistoricalStrikeSelectionPolicy(
            max_finish_outside_probability=0.15,
            max_reached_probability=0.30,
        ),
    )

    assert selection.call_recommendation is not None
    assert (
        selection.call_recommendation.reason
        is HistoricalStrikeSelectionReason.EXPECTED_MOVE_MATCH
    )

    assert selection.put_recommendation is not None
    assert (
        selection.put_recommendation.reason
        is HistoricalStrikeSelectionReason.EXPECTED_MOVE_MATCH
    )


def test_returns_none_when_no_strike_meets_policy() -> None:
    selection = HistoricalStrikeSelector().select(
        risk_grid=make_grid(),
        expected_move_percent=9.0,
        policy=HistoricalStrikeSelectionPolicy(
            max_finish_outside_probability=0.01,
            max_reached_probability=0.05,
        ),
    )

    assert selection.call_recommendation is None
    assert selection.put_recommendation is None


def test_reached_probability_can_be_ignored() -> None:
    selection = HistoricalStrikeSelector().select(
        risk_grid=make_grid(),
        expected_move_percent=9.0,
        policy=HistoricalStrikeSelectionPolicy(
            max_finish_outside_probability=0.15,
            max_reached_probability=None,
        ),
    )

    assert selection.call_recommendation is not None
    assert (
        selection.call_recommendation
        .recommended_threshold_percent
        == pytest.approx(10.0)
    )

    assert selection.put_recommendation is not None
    assert (
        selection.put_recommendation
        .recommended_threshold_percent
        == pytest.approx(-10.0)
    )


def test_allows_one_sided_grid() -> None:
    grid = HistoricalStrikeRiskGrid(
        call_risks=make_grid().call_risks,
        put_risks=(),
    )

    selection = HistoricalStrikeSelector().select(
        risk_grid=grid,
        expected_move_percent=9.0,
        policy=HistoricalStrikeSelectionPolicy(
            max_finish_outside_probability=0.10,
            max_reached_probability=0.25,
        ),
    )

    assert selection.call_recommendation is not None
    assert selection.put_recommendation is None


def test_prefers_farther_strike_on_equal_distance() -> None:
    grid = HistoricalStrikeRiskGrid(
        call_risks=(
            make_risk(
                side=StrikeSide.CALL,
                threshold_percent=7.5,
                finish_outside_probability=0.08,
                reached_probability=0.20,
            ),
            make_risk(
                side=StrikeSide.CALL,
                threshold_percent=10.0,
                finish_outside_probability=0.05,
                reached_probability=0.15,
            ),
        ),
        put_risks=(),
    )

    selection = HistoricalStrikeSelector().select(
        risk_grid=grid,
        expected_move_percent=8.75,
        policy=HistoricalStrikeSelectionPolicy(
            max_finish_outside_probability=0.10,
            max_reached_probability=0.25,
            prefer_farther_on_tie=True,
        ),
    )

    assert selection.call_recommendation is not None
    assert (
        selection.call_recommendation
        .recommended_threshold_percent
        == pytest.approx(10.0)
    )


def test_can_prefer_nearer_strike_on_equal_distance() -> None:
    grid = HistoricalStrikeRiskGrid(
        call_risks=(
            make_risk(
                side=StrikeSide.CALL,
                threshold_percent=7.5,
                finish_outside_probability=0.08,
                reached_probability=0.20,
            ),
            make_risk(
                side=StrikeSide.CALL,
                threshold_percent=10.0,
                finish_outside_probability=0.05,
                reached_probability=0.15,
            ),
        ),
        put_risks=(),
    )

    selection = HistoricalStrikeSelector().select(
        risk_grid=grid,
        expected_move_percent=8.75,
        policy=HistoricalStrikeSelectionPolicy(
            max_finish_outside_probability=0.10,
            max_reached_probability=0.25,
            prefer_farther_on_tie=False,
        ),
    )

    assert selection.call_recommendation is not None
    assert (
        selection.call_recommendation
        .recommended_threshold_percent
        == pytest.approx(7.5)
    )


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
        HistoricalStrikeSelector().select(
            risk_grid=make_grid(),
            expected_move_percent=expected_move_percent,
            policy=HistoricalStrikeSelectionPolicy(
                max_finish_outside_probability=0.10,
            ),
        )


@pytest.mark.parametrize(
    "probability",
    (
        -0.01,
        1.01,
    ),
)
def test_rejects_invalid_finish_outside_probability(
    probability: float,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "max_finish_outside_probability must be "
            "between 0 and 1"
        ),
    ):
        HistoricalStrikeSelectionPolicy(
            max_finish_outside_probability=probability,
        )


@pytest.mark.parametrize(
    "probability",
    (
        -0.01,
        1.01,
    ),
)
def test_rejects_invalid_reached_probability(
    probability: float,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "max_reached_probability must be "
            "between 0 and 1"
        ),
    ):
        HistoricalStrikeSelectionPolicy(
            max_finish_outside_probability=0.10,
            max_reached_probability=probability,
        )


def test_rejects_inconsistent_call_risk_side() -> None:
    invalid_grid = HistoricalStrikeRiskGrid(
        call_risks=(
            make_risk(
                side=StrikeSide.PUT,
                threshold_percent=-10.0,
                finish_outside_probability=0.05,
                reached_probability=0.10,
            ),
        ),
        put_risks=(),
    )

    with pytest.raises(
        ValueError,
        match="call risks must all use call side",
    ):
        HistoricalStrikeSelector().select(
            risk_grid=invalid_grid,
            expected_move_percent=10.0,
            policy=HistoricalStrikeSelectionPolicy(
                max_finish_outside_probability=0.10,
            ),
        )