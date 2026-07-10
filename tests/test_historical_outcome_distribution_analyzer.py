from datetime import date

import pytest

from app.analysis.historical_outcome_analyzer import (
    HistoricalOutcome,
)
from app.analysis.historical_outcome_distribution_analyzer import (
    HistoricalOutcomeDistributionAnalyzer,
)


def make_outcome(
    exit_trading_day_index: int,
    exit_date: date,
    exit_close_percent: float,
    highest_percent_until_exit: float,
    lowest_percent_until_exit: float,
) -> HistoricalOutcome:
    return HistoricalOutcome(
        exit_trading_day_index=exit_trading_day_index,
        exit_date=exit_date,
        exit_close_percent=exit_close_percent,
        highest_percent_until_exit=(
            highest_percent_until_exit
        ),
        lowest_percent_until_exit=(
            lowest_percent_until_exit
        ),
        trading_days_observed=exit_trading_day_index,
    )


def test_calculates_distribution_for_selected_exit_day() -> None:
    outcomes = (
        make_outcome(
            exit_trading_day_index=2,
            exit_date=date(2025, 10, 20),
            exit_close_percent=8.0,
            highest_percent_until_exit=15.0,
            lowest_percent_until_exit=-5.0,
        ),
        make_outcome(
            exit_trading_day_index=2,
            exit_date=date(2026, 1, 22),
            exit_close_percent=-4.0,
            highest_percent_until_exit=6.0,
            lowest_percent_until_exit=-12.0,
        ),
        make_outcome(
            exit_trading_day_index=2,
            exit_date=date(2026, 4, 20),
            exit_close_percent=2.0,
            highest_percent_until_exit=9.0,
            lowest_percent_until_exit=-3.0,
        ),
    )

    distributions = (
        HistoricalOutcomeDistributionAnalyzer().analyze(
            outcomes
        )
    )

    assert len(distributions) == 1

    distribution = distributions[0]

    assert distribution.exit_trading_day_index == 2
    assert distribution.observation_count == 3

    exit_close = distribution.exit_close_distribution
    assert exit_close.observation_count == 3
    assert exit_close.average_percent == pytest.approx(
        2.0
    )
    assert exit_close.median_percent == pytest.approx(
        2.0
    )
    assert exit_close.minimum_percent == pytest.approx(
        -4.0
    )
    assert exit_close.maximum_percent == pytest.approx(
        8.0
    )
    assert exit_close.percentile_25 == pytest.approx(
        -1.0
    )
    assert exit_close.percentile_75 == pytest.approx(
        5.0
    )
    assert exit_close.positive_ratio == pytest.approx(
        2 / 3
    )
    assert exit_close.negative_ratio == pytest.approx(
        1 / 3
    )
    assert exit_close.unchanged_ratio == pytest.approx(
        0.0
    )

    highest = (
        distribution.highest_until_exit_distribution
    )
    assert highest.average_percent == pytest.approx(
        10.0
    )
    assert highest.minimum_percent == pytest.approx(
        6.0
    )
    assert highest.maximum_percent == pytest.approx(
        15.0
    )

    lowest = (
        distribution.lowest_until_exit_distribution
    )
    assert lowest.average_percent == pytest.approx(
        -20 / 3
    )
    assert lowest.minimum_percent == pytest.approx(
        -12.0
    )
    assert lowest.maximum_percent == pytest.approx(
        -3.0
    )


def test_groups_outcomes_by_exit_trading_day() -> None:
    outcomes = (
        make_outcome(
            exit_trading_day_index=2,
            exit_date=date(2026, 1, 22),
            exit_close_percent=5.0,
            highest_percent_until_exit=8.0,
            lowest_percent_until_exit=-3.0,
        ),
        make_outcome(
            exit_trading_day_index=1,
            exit_date=date(2026, 1, 21),
            exit_close_percent=3.0,
            highest_percent_until_exit=6.0,
            lowest_percent_until_exit=-2.0,
        ),
        make_outcome(
            exit_trading_day_index=2,
            exit_date=date(2026, 4, 20),
            exit_close_percent=-1.0,
            highest_percent_until_exit=4.0,
            lowest_percent_until_exit=-7.0,
        ),
    )

    distributions = (
        HistoricalOutcomeDistributionAnalyzer().analyze(
            outcomes
        )
    )

    assert tuple(
        distribution.exit_trading_day_index
        for distribution in distributions
    ) == (
        1,
        2,
    )

    assert distributions[0].observation_count == 1
    assert distributions[1].observation_count == 2

    assert (
        distributions[1]
        .exit_close_distribution
        .average_percent
        == pytest.approx(2.0)
    )


def test_calculates_single_observation_distribution() -> None:
    outcome = make_outcome(
        exit_trading_day_index=3,
        exit_date=date(2026, 4, 21),
        exit_close_percent=7.5,
        highest_percent_until_exit=12.0,
        lowest_percent_until_exit=-4.0,
    )

    distributions = (
        HistoricalOutcomeDistributionAnalyzer().analyze(
            (outcome,)
        )
    )

    distribution = distributions[0]
    exit_close = distribution.exit_close_distribution

    assert distribution.observation_count == 1
    assert exit_close.average_percent == pytest.approx(
        7.5
    )
    assert exit_close.median_percent == pytest.approx(
        7.5
    )
    assert exit_close.percentile_25 == pytest.approx(
        7.5
    )
    assert exit_close.percentile_75 == pytest.approx(
        7.5
    )
    assert exit_close.positive_ratio == pytest.approx(
        1.0
    )


def test_calculates_unchanged_exit_ratio() -> None:
    outcomes = (
        make_outcome(
            exit_trading_day_index=1,
            exit_date=date(2026, 1, 21),
            exit_close_percent=0.0,
            highest_percent_until_exit=4.0,
            lowest_percent_until_exit=-3.0,
        ),
        make_outcome(
            exit_trading_day_index=1,
            exit_date=date(2026, 4, 17),
            exit_close_percent=2.0,
            highest_percent_until_exit=5.0,
            lowest_percent_until_exit=-1.0,
        ),
    )

    distributions = (
        HistoricalOutcomeDistributionAnalyzer().analyze(
            outcomes
        )
    )

    exit_close = (
        distributions[0].exit_close_distribution
    )

    assert exit_close.positive_ratio == pytest.approx(
        0.5
    )
    assert exit_close.negative_ratio == pytest.approx(
        0.0
    )
    assert exit_close.unchanged_ratio == pytest.approx(
        0.5
    )


def test_returns_empty_result_without_outcomes() -> None:
    distributions = (
        HistoricalOutcomeDistributionAnalyzer().analyze(
            ()
        )
    )

    assert distributions == ()


def test_rejects_invalid_exit_trading_day_index() -> None:
    outcome = make_outcome(
        exit_trading_day_index=0,
        exit_date=date(2026, 4, 17),
        exit_close_percent=2.0,
        highest_percent_until_exit=5.0,
        lowest_percent_until_exit=-3.0,
    )

    with pytest.raises(
        ValueError,
        match=(
            "exit_trading_day_index must be at least 1"
        ),
    ):
        HistoricalOutcomeDistributionAnalyzer().analyze(
            (outcome,)
        )