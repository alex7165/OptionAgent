from datetime import date

import pytest

from app.analysis.management_strategy_knn_model import (
    ManagementStrategyKnnModel,
)
from app.analysis.training_dataset import TrainingDataset
from app.analysis.training_example import TrainingExample


def _example(
    *,
    earnings_date: date,
    reaction_move: float,
    label: str,
    expected_move: float | None = 8.0,
    friday_move: float = 0.0,
) -> TrainingExample:
    return TrainingExample(
        symbol="GS",
        earnings_date=earnings_date,
        report_timing="amc",
        reference_price=100.0,
        entry_strategy="short_strangle",
        expected_move_percent=expected_move,
        short_put_distance_percent=-8.0,
        short_call_distance_percent=10.0,
        first_reaction_move_percent=reaction_move,
        maximum_move_percent=abs(friday_move) + 2.0,
        friday_close_move_percent=friday_move,
        made_all_time_high=friday_move > 0,
        best_management_strategy=label,
    )


def test_predicts_strategy_of_nearest_historical_cases() -> None:
    dataset = TrainingDataset(
        examples=(
            _example(
                earnings_date=date(2023, 1, 1),
                reaction_move=2.0,
                label="hold_until_friday",
            ),
            _example(
                earnings_date=date(2024, 1, 1),
                reaction_move=2.5,
                label="hold_until_friday",
            ),
            _example(
                earnings_date=date(2025, 1, 1),
                reaction_move=12.0,
                label="roll_to_new_strike",
            ),
        )
    )
    query = _example(
        earnings_date=date(2026, 1, 1),
        reaction_move=11.5,
        label="ignored",
    )

    prediction = ManagementStrategyKnnModel(k=1).fit(dataset).predict(query)

    assert prediction == "roll_to_new_strike"


def test_prediction_does_not_use_future_outcome_fields() -> None:
    dataset = TrainingDataset(
        examples=(
            _example(
                earnings_date=date(2023, 1, 1),
                reaction_move=3.0,
                friday_move=-20.0,
                label="close_day1",
            ),
            _example(
                earnings_date=date(2024, 1, 1),
                reaction_move=10.0,
                friday_move=20.0,
                label="roll_to_new_strike",
            ),
        )
    )
    model = ManagementStrategyKnnModel(k=1).fit(dataset)
    first_query = _example(
        earnings_date=date(2026, 1, 1),
        reaction_move=3.1,
        friday_move=-99.0,
        label="ignored",
    )
    second_query = _example(
        earnings_date=date(2026, 1, 1),
        reaction_move=3.1,
        friday_move=99.0,
        label="ignored",
    )

    assert model.predict(first_query) == "close_day1"
    assert model.predict(second_query) == "close_day1"


def test_uses_training_mean_when_expected_move_is_missing() -> None:
    dataset = TrainingDataset(
        examples=(
            _example(
                earnings_date=date(2023, 1, 1),
                reaction_move=2.0,
                expected_move=6.0,
                label="hold_until_friday",
            ),
            _example(
                earnings_date=date(2024, 1, 1),
                reaction_move=9.0,
                expected_move=10.0,
                label="roll_to_new_strike",
            ),
        )
    )
    query = _example(
        earnings_date=date(2026, 1, 1),
        reaction_move=2.1,
        expected_move=None,
        label="ignored",
    )

    prediction = ManagementStrategyKnnModel(k=1).fit(dataset).predict(query)

    assert prediction == "hold_until_friday"


def test_rejects_prediction_before_fit() -> None:
    query = _example(
        earnings_date=date(2026, 1, 1),
        reaction_move=2.0,
        label="ignored",
    )

    with pytest.raises(RuntimeError, match="must be fitted"):
        ManagementStrategyKnnModel().predict(query)
