from datetime import date

import pytest

from app.analysis.historical_outcome_analyzer import (
    HistoricalOutcome,
)
from app.analysis.historical_strike_risk_analyzer import (
    HistoricalStrikeRiskAnalyzer,
    StrikeSide,
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


def test_calculates_call_strike_risk() -> None:
    outcomes = (
        make_outcome(
            exit_close_percent=12.0,
            highest_percent_until_exit=15.0,
            lowest_percent_until_exit=-3.0,
        ),
        make_outcome(
            exit_close_percent=8.0,
            highest_percent_until_exit=13.0,
            lowest_percent_until_exit=-5.0,
        ),
        make_outcome(
            exit_close_percent=4.0,
            highest_percent_until_exit=7.0,
            lowest_percent_until_exit=-6.0,
        ),
        make_outcome(
            exit_close_percent=-2.0,
            highest_percent_until_exit=3.0,
            lowest_percent_until_exit=-9.0,
        ),
    )

    risk = HistoricalStrikeRiskAnalyzer().analyze(
        outcomes=outcomes,
        side=StrikeSide.CALL,
        threshold_percent=10.0,
    )

    assert risk.side is StrikeSide.CALL
    assert risk.threshold_percent == 10.0
    assert risk.exit_trading_day_index == 2
    assert risk.observation_count == 4

    assert (
        risk.finish_outside_probability
        == pytest.approx(0.25)
    )
    assert (
        risk.finish_inside_probability
        == pytest.approx(0.75)
    )
    assert risk.reached_probability == pytest.approx(
        0.5
    )
    assert (
        risk.worst_historical_move_percent
        == pytest.approx(15.0)
    )


def test_calculates_put_strike_risk() -> None:
    outcomes = (
        make_outcome(
            exit_close_percent=-12.0,
            highest_percent_until_exit=4.0,
            lowest_percent_until_exit=-15.0,
        ),
        make_outcome(
            exit_close_percent=-8.0,
            highest_percent_until_exit=6.0,
            lowest_percent_until_exit=-13.0,
        ),
        make_outcome(
            exit_close_percent=-4.0,
            highest_percent_until_exit=8.0,
            lowest_percent_until_exit=-7.0,
        ),
        make_outcome(
            exit_close_percent=2.0,
            highest_percent_until_exit=10.0,
            lowest_percent_until_exit=-3.0,
        ),
    )

    risk = HistoricalStrikeRiskAnalyzer().analyze(
        outcomes=outcomes,
        side=StrikeSide.PUT,
        threshold_percent=-10.0,
    )

    assert risk.side is StrikeSide.PUT
    assert risk.threshold_percent == -10.0
    assert risk.exit_trading_day_index == 2
    assert risk.observation_count == 4

    assert (
        risk.finish_outside_probability
        == pytest.approx(0.25)
    )
    assert (
        risk.finish_inside_probability
        == pytest.approx(0.75)
    )
    assert risk.reached_probability == pytest.approx(
        0.5
    )
    assert (
        risk.worst_historical_move_percent
        == pytest.approx(-15.0)
    )


def test_strike_equal_to_exit_close_finishes_inside() -> None:
    outcome = make_outcome(
        exit_close_percent=10.0,
        highest_percent_until_exit=12.0,
        lowest_percent_until_exit=-3.0,
    )

    risk = HistoricalStrikeRiskAnalyzer().analyze(
        outcomes=(outcome,),
        side=StrikeSide.CALL,
        threshold_percent=10.0,
    )

    assert risk.finish_inside_probability == pytest.approx(
        1.0
    )
    assert risk.finish_outside_probability == pytest.approx(
        0.0
    )
    assert risk.reached_probability == pytest.approx(
        1.0
    )


def test_threshold_equal_to_intraday_extreme_counts_as_reached() -> None:
    outcome = make_outcome(
        exit_close_percent=5.0,
        highest_percent_until_exit=10.0,
        lowest_percent_until_exit=-10.0,
    )

    call_risk = HistoricalStrikeRiskAnalyzer().analyze(
        outcomes=(outcome,),
        side=StrikeSide.CALL,
        threshold_percent=10.0,
    )
    put_risk = HistoricalStrikeRiskAnalyzer().analyze(
        outcomes=(outcome,),
        side=StrikeSide.PUT,
        threshold_percent=-10.0,
    )

    assert call_risk.reached_probability == pytest.approx(
        1.0
    )
    assert put_risk.reached_probability == pytest.approx(
        1.0
    )


def test_rejects_empty_outcomes() -> None:
    with pytest.raises(
        ValueError,
        match="outcomes must not be empty",
    ):
        HistoricalStrikeRiskAnalyzer().analyze(
            outcomes=(),
            side=StrikeSide.CALL,
            threshold_percent=10.0,
        )


@pytest.mark.parametrize(
    "threshold_percent",
    (
        0.0,
        -10.0,
    ),
)
def test_rejects_invalid_call_threshold(
    threshold_percent: float,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Call threshold_percent must be "
            "greater than zero"
        ),
    ):
        HistoricalStrikeRiskAnalyzer().analyze(
            outcomes=(
                make_outcome(
                    exit_close_percent=5.0,
                    highest_percent_until_exit=8.0,
                    lowest_percent_until_exit=-4.0,
                ),
            ),
            side=StrikeSide.CALL,
            threshold_percent=threshold_percent,
        )


@pytest.mark.parametrize(
    "threshold_percent",
    (
        0.0,
        10.0,
    ),
)
def test_rejects_invalid_put_threshold(
    threshold_percent: float,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Put threshold_percent must be "
            "less than zero"
        ),
    ):
        HistoricalStrikeRiskAnalyzer().analyze(
            outcomes=(
                make_outcome(
                    exit_close_percent=-5.0,
                    highest_percent_until_exit=4.0,
                    lowest_percent_until_exit=-8.0,
                ),
            ),
            side=StrikeSide.PUT,
            threshold_percent=threshold_percent,
        )


def test_rejects_mixed_exit_trading_days() -> None:
    outcomes = (
        make_outcome(
            exit_close_percent=5.0,
            highest_percent_until_exit=8.0,
            lowest_percent_until_exit=-4.0,
            exit_trading_day_index=1,
        ),
        make_outcome(
            exit_close_percent=7.0,
            highest_percent_until_exit=11.0,
            lowest_percent_until_exit=-5.0,
            exit_trading_day_index=2,
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "outcomes must use the same "
            "exit_trading_day_index"
        ),
    ):
        HistoricalStrikeRiskAnalyzer().analyze(
            outcomes=outcomes,
            side=StrikeSide.CALL,
            threshold_percent=10.0,
        )