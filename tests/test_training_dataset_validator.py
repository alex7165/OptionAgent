from dataclasses import replace
from datetime import date

from app.analysis.training_dataset import TrainingDataset
from app.analysis.training_dataset_validator import TrainingDatasetValidator
from app.analysis.training_example import TrainingExample


def _example(
    *,
    symbol: str = "GS",
    earnings_date: date = date(2026, 7, 14),
    expected_move_percent: float | None = 8.4,
) -> TrainingExample:
    return TrainingExample(
        symbol=symbol,
        earnings_date=earnings_date,
        report_timing="amc",
        reference_price=100.0,
        entry_strategy="short_strangle",
        expected_move_percent=expected_move_percent,
        short_put_distance_percent=8.0,
        short_call_distance_percent=10.0,
        first_reaction_move_percent=10.1,
        maximum_move_percent=12.0,
        friday_close_move_percent=7.0,
        made_all_time_high=True,
        best_management_strategy="hold_until_friday",
    )


def test_accepts_valid_training_dataset() -> None:
    result = TrainingDatasetValidator().validate(
        TrainingDataset(examples=(_example(),))
    )

    assert result.valid is True
    assert result.errors == ()
    assert result.warnings == ()


def test_rejects_empty_and_duplicate_examples() -> None:
    validator = TrainingDatasetValidator()

    empty_result = validator.validate(TrainingDataset(examples=()))
    duplicate_result = validator.validate(
        TrainingDataset(examples=(_example(), _example()))
    )

    assert empty_result.valid is False
    assert empty_result.errors == (
        "Training dataset must contain at least one example",
    )
    assert duplicate_result.valid is False
    assert duplicate_result.errors == (
        "Duplicate training example: GS 2026-07-14",
    )


def test_reports_invalid_numbers_and_missing_optional_expected_move() -> None:
    invalid = replace(_example(), friday_close_move_percent=float("nan"))
    missing_expected_move = _example(
        symbol="JPM",
        earnings_date=date(2025, 7, 15),
        expected_move_percent=None,
    )

    result = TrainingDatasetValidator().validate(
        TrainingDataset(examples=(invalid, missing_expected_move))
    )

    assert result.valid is False
    assert result.errors == (
        "Example 1 has invalid friday_close_move_percent",
    )
    assert result.warnings == (
        "Example 2 has no expected_move_percent",
    )
