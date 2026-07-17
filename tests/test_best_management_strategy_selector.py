import pytest

from app.analysis.best_management_strategy_selector import (
    BestManagementStrategySelector,
)
from app.analysis.management_outcome import ManagementOutcome
from app.analysis.management_strategy_score import ManagementStrategyScore


def _outcome(
    strategy_name: str,
    *,
    overall_score: float,
    risk_score: float,
    exit_day: int,
) -> ManagementOutcome:
    return ManagementOutcome(
        strategy_name=strategy_name,
        entry_day=1,
        exit_day=exit_day,
        exit_reason="test",
        max_adverse_move=0.0,
        max_favorable_move=0.0,
        finished_inside_strikes=True,
        all_time_high_after_entry=False,
        final_move_percent=0.0,
        score=ManagementStrategyScore(
            success_score=100.0,
            risk_score=risk_score,
            reward_score=0.0,
            overall_score=overall_score,
        ),
    )


def test_selects_highest_overall_score() -> None:
    selector = BestManagementStrategySelector()
    close_day1 = _outcome(
        "close_day1",
        overall_score=70.0,
        risk_score=20.0,
        exit_day=1,
    )
    hold_friday = _outcome(
        "hold_until_friday",
        overall_score=82.0,
        risk_score=35.0,
        exit_day=4,
    )

    result = selector.select_best((close_day1, hold_friday))

    assert result is hold_friday


def test_uses_lower_risk_score_as_first_tiebreaker() -> None:
    selector = BestManagementStrategySelector()
    lower_risk = _outcome(
        "lower_risk",
        overall_score=80.0,
        risk_score=15.0,
        exit_day=4,
    )
    higher_risk = _outcome(
        "higher_risk",
        overall_score=80.0,
        risk_score=30.0,
        exit_day=1,
    )

    result = selector.select_best((higher_risk, lower_risk))

    assert result is lower_risk


def test_uses_earlier_exit_day_as_second_tiebreaker() -> None:
    selector = BestManagementStrategySelector()
    early_exit = _outcome(
        "early_exit",
        overall_score=80.0,
        risk_score=20.0,
        exit_day=1,
    )
    late_exit = _outcome(
        "late_exit",
        overall_score=80.0,
        risk_score=20.0,
        exit_day=4,
    )

    result = selector.select_best((late_exit, early_exit))

    assert result is early_exit


def test_rejects_empty_outcomes() -> None:
    selector = BestManagementStrategySelector()

    with pytest.raises(ValueError, match="outcomes must not be empty"):
        selector.select_best(())


def test_rejects_unscored_outcome() -> None:
    selector = BestManagementStrategySelector()
    unscored = ManagementOutcome(
        strategy_name="unscored",
        entry_day=1,
        exit_day=1,
        exit_reason="test",
        max_adverse_move=0.0,
        max_favorable_move=0.0,
        finished_inside_strikes=True,
        all_time_high_after_entry=False,
        final_move_percent=0.0,
    )

    with pytest.raises(ValueError, match="all outcomes must be scored: unscored"):
        selector.select_best((unscored,))
