from __future__ import annotations

import math
from dataclasses import dataclass

from app.analysis.training_dataset import TrainingDataset
from app.analysis.training_example import TrainingExample


@dataclass(frozen=True, slots=True)
class TrainingDatasetValidationResult:
    """Validation result for an in-memory management training dataset."""

    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...] = ()


class TrainingDatasetValidator:
    """Checks training data consistency before export or model training."""

    _NUMERIC_FIELDS = (
        "reference_price",
        "short_put_distance_percent",
        "short_call_distance_percent",
        "first_reaction_move_percent",
        "maximum_move_percent",
        "friday_close_move_percent",
    )

    def validate(self, dataset: TrainingDataset) -> TrainingDatasetValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        if not dataset.examples:
            errors.append("Training dataset must contain at least one example")
            return TrainingDatasetValidationResult(
                valid=False,
                errors=tuple(errors),
                warnings=tuple(warnings),
            )

        seen_keys: set[tuple[str, object]] = set()

        for index, example in enumerate(dataset.examples, start=1):
            key = (example.symbol, example.earnings_date)
            if key in seen_keys:
                errors.append(
                    "Duplicate training example: "
                    f"{example.symbol} {example.earnings_date.isoformat()}"
                )
            seen_keys.add(key)

            self._validate_required_text(example, index, errors)
            self._validate_numeric_fields(example, index, errors)

            if example.expected_move_percent is None:
                warnings.append(
                    f"Example {index} has no expected_move_percent"
                )
            elif not math.isfinite(example.expected_move_percent):
                errors.append(
                    f"Example {index} has invalid expected_move_percent"
                )

        return TrainingDatasetValidationResult(
            valid=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    @staticmethod
    def _validate_required_text(
        example: TrainingExample,
        index: int,
        errors: list[str],
    ) -> None:
        required_text_fields = (
            "symbol",
            "report_timing",
            "entry_strategy",
            "best_management_strategy",
        )
        for field_name in required_text_fields:
            value = getattr(example, field_name)
            if not isinstance(value, str) or not value.strip():
                errors.append(
                    f"Example {index} has missing {field_name}"
                )

    def _validate_numeric_fields(
        self,
        example: TrainingExample,
        index: int,
        errors: list[str],
    ) -> None:
        for field_name in self._NUMERIC_FIELDS:
            value = getattr(example, field_name)
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                errors.append(
                    f"Example {index} has invalid {field_name}"
                )
