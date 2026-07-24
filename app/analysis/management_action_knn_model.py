from __future__ import annotations

import math
from dataclasses import dataclass

from app.analysis.management_action import ManagementAction, ThreatenedSide
from app.analysis.management_action_training_dataset import ManagementActionTrainingDataset
from app.analysis.management_action_training_example import ManagementActionTrainingExample


@dataclass(frozen=True, slots=True)
class SimilarManagementCase:
    symbol: str
    action: ManagementAction
    distance: float
    total_profit_loss: float


@dataclass(frozen=True, slots=True)
class ManagementActionPrediction:
    action: ManagementAction
    predicted_profit_loss: float
    confidence: float
    similar_cases: tuple[SimilarManagementCase, ...]


@dataclass(frozen=True, slots=True)
class _PreparedActionExample:
    source: ManagementActionTrainingExample
    numeric_features: tuple[float, ...]


class ManagementActionKnnModel:
    """Predict action P/L from comparable situation + action rows.

    Only complete historical P/L rows are fitted. Outcome fields from the query
    are never used as features, preventing future-data leakage.
    """

    def __init__(self, k: int = 5) -> None:
        if k <= 0:
            raise ValueError("k must be greater than zero")
        self.k = k
        self._examples: tuple[_PreparedActionExample, ...] = ()
        self._means: tuple[float, ...] = ()
        self._scales: tuple[float, ...] = ()
        self._fallbacks: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)

    def fit(self, dataset: ManagementActionTrainingDataset) -> ManagementActionKnnModel:
        complete = tuple(
            example
            for example in dataset.examples
            if example.complete_profit_loss and example.total_profit_loss is not None
        )
        if not complete:
            raise ValueError("dataset must contain at least one complete P/L row")

        self._fallbacks = (
            self._mean_optional(complete, "short_option_delta"),
            self._mean_optional(complete, "expected_move_percent"),
            self._mean_optional(complete, "iv_rank"),
            self._mean_optional(complete, "iv_percentile"),
        )
        raw = tuple(self._numeric_vector(example) for example in complete)
        self._means = tuple(
            sum(vector[index] for vector in raw) / len(raw)
            for index in range(len(raw[0]))
        )
        self._scales = tuple(
            self._standard_deviation(raw, index)
            for index in range(len(raw[0]))
        )
        self._examples = tuple(
            _PreparedActionExample(example, self._standardize(vector))
            for example, vector in zip(complete, raw, strict=True)
        )
        return self

    def predict(self, query: ManagementActionTrainingExample) -> ManagementActionPrediction:
        if not self._examples:
            raise RuntimeError("model must be fitted before prediction")

        query_vector = self._standardize(self._numeric_vector(query))
        ranked = sorted(
            [
                (
                    self._distance(query_vector, query, prepared),
                    prepared.source,
                )
                for prepared in self._examples
                if prepared.source.action is query.action
            ],
            key=lambda item: (item[0], item[1].symbol),
        )
        if not ranked:
            raise ValueError(f"no training rows for action {query.action.value}")

        neighbours = ranked[: min(self.k, len(ranked))]
        weights = tuple(1.0 / (distance + 1e-9) for distance, _ in neighbours)
        weight_sum = sum(weights)
        predicted = sum(
            weight * float(example.total_profit_loss)
            for weight, (_, example) in zip(weights, neighbours, strict=True)
        ) / weight_sum
        confidence = max(0.0, min(1.0, 1.0 / (1.0 + sum(d for d, _ in neighbours) / len(neighbours))))

        return ManagementActionPrediction(
            action=query.action,
            predicted_profit_loss=predicted,
            confidence=confidence,
            similar_cases=tuple(
                SimilarManagementCase(
                    symbol=example.symbol,
                    action=example.action,
                    distance=distance,
                    total_profit_loss=float(example.total_profit_loss),
                )
                for distance, example in neighbours
            ),
        )

    def select_best(
        self,
        candidates: tuple[ManagementActionTrainingExample, ...],
    ) -> ManagementActionPrediction:
        if not candidates:
            raise ValueError("candidates must not be empty")
        predictions = tuple(self.predict(candidate) for candidate in candidates)
        return max(
            predictions,
            key=lambda result: (result.predicted_profit_loss, result.confidence, result.action.value),
        )

    def _numeric_vector(self, example: ManagementActionTrainingExample) -> tuple[float, ...]:
        delta, expected_move, iv_rank, iv_percentile = self._fallbacks
        return (
            float(example.trading_day_index),
            float(example.strike_distance_percent),
            float(example.days_to_expiration),
            float(example.short_option_delta if example.short_option_delta is not None else delta),
            float(example.expected_move_percent if example.expected_move_percent is not None else expected_move),
            float(example.iv_rank if example.iv_rank is not None else iv_rank),
            float(example.iv_percentile if example.iv_percentile is not None else iv_percentile),
        )

    def _standardize(self, vector: tuple[float, ...]) -> tuple[float, ...]:
        return tuple(
            (value - mean) / scale
            for value, mean, scale in zip(vector, self._means, self._scales, strict=True)
        )

    @staticmethod
    def _mean_optional(examples: tuple[ManagementActionTrainingExample, ...], field: str) -> float:
        values = tuple(float(value) for example in examples if (value := getattr(example, field)) is not None)
        return sum(values) / len(values) if values else 0.0

    @staticmethod
    def _standard_deviation(vectors: tuple[tuple[float, ...], ...], index: int) -> float:
        mean = sum(vector[index] for vector in vectors) / len(vectors)
        variance = sum((vector[index] - mean) ** 2 for vector in vectors) / len(vectors)
        deviation = math.sqrt(variance)
        return deviation if deviation > 0 else 1.0

    @staticmethod
    def _distance(
        query_vector: tuple[float, ...],
        query: ManagementActionTrainingExample,
        prepared: _PreparedActionExample,
    ) -> float:
        numeric = math.sqrt(sum((a - b) ** 2 for a, b in zip(query_vector, prepared.numeric_features, strict=True)))
        penalty = 0.0
        source = prepared.source
        if source.threatened_side is not query.threatened_side:
            penalty += 2.0
        if source.entry_strategy != query.entry_strategy:
            penalty += 1.0
        return numeric + penalty
