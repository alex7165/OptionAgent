from datetime import date

import pytest

from app.analysis.management_strategy_model_evaluator import (
    ManagementStrategyModelEvaluator,
)
from app.analysis.training_dataset import TrainingDataset
from app.analysis.training_example import TrainingExample


def _example(
    *,
    day: int,
    reaction_move: float,
    label: str,
) -> TrainingExample:
    return TrainingExample(
        symbol=f"T{day}",
        earnings_date=date(2026, 1, day),
        report_timing="amc",
        reference_price=100.0,
        entry_strategy="short_strangle",
        expected_move_percent=8.0,
        short_put_distance_percent=-8.0,
        short_call_distance_percent=10.0,
        first_reaction_move_percent=reaction_move,
        maximum_move_percent=abs(reaction_move),
        friday_close_move_percent=reaction_move,
        made_all_time_high=reaction_move > 0,
        best_management_strategy=label,
    )


def test_evaluates_model_with_leave_one_out_cross_validation() -> None:
    dataset = TrainingDataset(
        examples=(
            _example(day=1, reaction_move=1.0, label="hold_until_friday"),
            _example(day=2, reaction_move=1.2, label="hold_until_friday"),
            _example(day=3, reaction_move=10.0, label="roll_to_new_strike"),
            _example(day=4, reaction_move=10.2, label="roll_to_new_strike"),
        )
    )

    result = ManagementStrategyModelEvaluator(k=1).evaluate(dataset)

    assert result.total_examples == 4
    assert result.correct_predictions == 4
    assert result.accuracy == 1.0


def test_returns_precision_and_recall_for_each_label() -> None:
    dataset = TrainingDataset(
        examples=(
            _example(day=1, reaction_move=1.0, label="hold_until_friday"),
            _example(day=2, reaction_move=1.1, label="hold_until_friday"),
            _example(day=3, reaction_move=9.0, label="roll_to_new_strike"),
            _example(day=4, reaction_move=9.1, label="roll_to_new_strike"),
        )
    )

    result = ManagementStrategyModelEvaluator(k=1).evaluate(dataset)
    metrics = {metric.label: metric for metric in result.class_metrics}

    assert metrics["hold_until_friday"].support == 2
    assert metrics["hold_until_friday"].precision == 1.0
    assert metrics["hold_until_friday"].recall == 1.0
    assert metrics["roll_to_new_strike"].support == 2


def test_rejects_dataset_with_only_one_example() -> None:
    dataset = TrainingDataset(
        examples=(
            _example(day=1, reaction_move=1.0, label="hold_until_friday"),
        )
    )

    with pytest.raises(ValueError, match="at least two examples"):
        ManagementStrategyModelEvaluator().evaluate(dataset)


def test_rejects_invalid_k() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        ManagementStrategyModelEvaluator(k=0)
