from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass

from app.analysis.training_dataset import TrainingDataset
from app.analysis.training_dataset_validator import TrainingDatasetValidator
from app.analysis.training_example import TrainingExample


@dataclass(frozen=True, slots=True)
class _PreparedExample:
    numeric_features: tuple[float, ...]
    report_timing: str
    entry_strategy: str
    label: str


class ManagementStrategyKnnModel:
    """Small dependency-free k-nearest-neighbours management classifier.

    Only information available when the management decision is made is used.
    Outcome fields such as the Friday close and maximum later move are excluded
    deliberately to prevent future-data leakage.
    """

    def __init__(self, k: int = 3) -> None:
        if k <= 0:
            raise ValueError("k must be greater than zero")
        self.k = k
        self._training_examples: tuple[_PreparedExample, ...] = ()
        self._means: tuple[float, ...] = ()
        self._scales: tuple[float, ...] = ()
        self._expected_move_fallback = 0.0

    def fit(self, dataset: TrainingDataset) -> ManagementStrategyKnnModel:
        validation = TrainingDatasetValidator().validate(dataset)
        if not validation.valid:
            raise ValueError(
                "invalid training dataset: " + "; ".join(validation.errors)
            )

        expected_moves = tuple(
            example.expected_move_percent
            for example in dataset.examples
            if example.expected_move_percent is not None
        )
        self._expected_move_fallback = (
            sum(expected_moves) / len(expected_moves) if expected_moves else 0.0
        )

        raw_vectors = tuple(
            self._numeric_vector(example) for example in dataset.examples
        )
        self._means = tuple(
            sum(vector[index] for vector in raw_vectors) / len(raw_vectors)
            for index in range(len(raw_vectors[0]))
        )
        self._scales = tuple(
            self._standard_deviation(raw_vectors, index)
            for index in range(len(raw_vectors[0]))
        )

        self._training_examples = tuple(
            _PreparedExample(
                numeric_features=self._standardize(vector),
                report_timing=example.report_timing,
                entry_strategy=example.entry_strategy,
                label=example.best_management_strategy,
            )
            for example, vector in zip(dataset.examples, raw_vectors, strict=True)
        )
        return self

    def predict(self, example: TrainingExample) -> str:
        if not self._training_examples:
            raise RuntimeError("model must be fitted before prediction")

        query = self._standardize(self._numeric_vector(example))
        distances = sorted(
            (
                self._distance(query, example, training),
                training.label,
            )
            for training in self._training_examples
        )
        neighbours = distances[: min(self.k, len(distances))]

        votes: dict[str, float] = defaultdict(float)
        total_distance: dict[str, float] = defaultdict(float)
        for distance, label in neighbours:
            votes[label] += 1.0 / (distance + 1e-9)
            total_distance[label] += distance

        return min(
            votes,
            key=lambda label: (
                -votes[label],
                total_distance[label],
                label,
            ),
        )

    def _numeric_vector(self, example: TrainingExample) -> tuple[float, ...]:
        expected_move = example.expected_move_percent
        if expected_move is None:
            expected_move = self._expected_move_fallback
        return (
            float(expected_move),
            float(example.short_put_distance_percent),
            float(example.short_call_distance_percent),
            float(example.first_reaction_move_percent),
        )

    def _standardize(self, vector: tuple[float, ...]) -> tuple[float, ...]:
        return tuple(
            (value - mean) / scale
            for value, mean, scale in zip(
                vector,
                self._means,
                self._scales,
                strict=True,
            )
        )

    @staticmethod
    def _standard_deviation(
        vectors: tuple[tuple[float, ...], ...],
        index: int,
    ) -> float:
        mean = sum(vector[index] for vector in vectors) / len(vectors)
        variance = sum(
            (vector[index] - mean) ** 2 for vector in vectors
        ) / len(vectors)
        standard_deviation = math.sqrt(variance)
        return standard_deviation if standard_deviation > 0 else 1.0

    @staticmethod
    def _distance(
        query: tuple[float, ...],
        example: TrainingExample,
        training: _PreparedExample,
    ) -> float:
        numeric_distance = math.sqrt(
            sum(
                (query_value - training_value) ** 2
                for query_value, training_value in zip(
                    query,
                    training.numeric_features,
                    strict=True,
                )
            )
        )
        category_penalty = 0.0
        if example.report_timing != training.report_timing:
            category_penalty += 1.0
        if example.entry_strategy != training.entry_strategy:
            category_penalty += 1.0
        return numeric_distance + category_penalty
