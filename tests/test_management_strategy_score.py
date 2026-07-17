import pytest

from app.analysis.management_outcome import ManagementOutcome
from app.analysis.management_strategy_score import ManagementStrategyScore


def test_score_rewards_success_and_limits_all_values_to_100() -> None:
    outcome = ManagementOutcome(
        strategy_name="hold_until_friday",
        entry_day=1,
        exit_day=4,
        exit_reason="friday_close",
        max_adverse_move=-3.0,
        max_favorable_move=5.0,
        finished_inside_strikes=True,
        all_time_high_after_entry=False,
        final_move_percent=2.0,
    )

    score = ManagementStrategyScore.from_outcome(outcome)

    assert score.success_score == 100.0
    assert score.risk_score == 30.0
    assert score.reward_score == 50.0
    assert score.overall_score == pytest.approx(77.5)


def test_score_penalizes_failed_high_risk_outcome() -> None:
    outcome = ManagementOutcome(
        strategy_name="roll_to_new_strike",
        entry_day=1,
        exit_day=4,
        exit_reason="friday_close",
        max_adverse_move=-12.0,
        max_favorable_move=1.0,
        finished_inside_strikes=False,
        all_time_high_after_entry=True,
        final_move_percent=9.0,
    )

    score = ManagementStrategyScore.from_outcome(outcome)

    assert score.success_score == 0.0
    assert score.risk_score == 100.0
    assert score.reward_score == 10.0
    assert score.overall_score == 0.0
