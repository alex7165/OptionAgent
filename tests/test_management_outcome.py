from dataclasses import FrozenInstanceError

import pytest

from app.analysis.management_outcome import ManagementOutcome


def test_management_outcome_stores_standardized_training_fields() -> None:
    outcome = ManagementOutcome(
        strategy_name="hold_until_friday",
        entry_day=1,
        exit_day=4,
        exit_reason="friday_close",
        max_adverse_move=-3.5,
        max_favorable_move=6.25,
        finished_inside_strikes=True,
        all_time_high_after_entry=False,
        final_move_percent=2.75,
    )

    assert outcome.strategy_name == "hold_until_friday"
    assert outcome.entry_day == 1
    assert outcome.exit_day == 4
    assert outcome.exit_reason == "friday_close"
    assert outcome.max_adverse_move == -3.5
    assert outcome.max_favorable_move == 6.25
    assert outcome.finished_inside_strikes is True
    assert outcome.all_time_high_after_entry is False
    assert outcome.final_move_percent == 2.75


def test_management_outcome_is_immutable() -> None:
    outcome = ManagementOutcome(
        strategy_name="close_after_reaction_day",
        entry_day=1,
        exit_day=1,
        exit_reason="reaction_day_close",
        max_adverse_move=-1.0,
        max_favorable_move=2.0,
        finished_inside_strikes=True,
        all_time_high_after_entry=False,
        final_move_percent=0.5,
    )

    with pytest.raises(FrozenInstanceError):
        outcome.exit_day = 2  # type: ignore[misc]
