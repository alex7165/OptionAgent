from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from app.analysis.management_strategy_knn_model import ManagementStrategyKnnModel
from app.analysis.training_dataset import TrainingDataset
from app.analysis.training_dataset_validator import TrainingDatasetValidator


@dataclass(frozen=True, slots=True)
class ManagementStrategyClassMetrics:
    label: str
    support: int
    predicted: int
    correct: int
    precision: float
    recall: float


@dataclass(frozen=True, slots=True)
class ManagementStrategyEvaluationResult:
    total_examples: int
    correct_predictions: int
    accuracy: float
    class_metrics: tuple[ManagementStrategyClassMetrics, ...]


class ManagementStrategyModelEvaluator:
    """Evaluates the KNN classifier with leave-one-out cross-validation."""

    def __init__(self, k: int = 3) -> None:
        if k <= 0:
            raise ValueError("k must be greater than zero")
        self.k = k

    def evaluate(
        self,
        dataset: TrainingDataset,
    ) -> ManagementStrategyEvaluationResult:
        validation = TrainingDatasetValidator().validate(dataset)
        if not validation.valid:
            raise ValueError(
                "invalid training dataset: " + "; ".join(validation.errors)
            )
        if len(dataset.examples) < 2:
            raise ValueError(
                "leave-one-out evaluation requires at least two examples"
            )

        actual_labels: list[str] = []
        predicted_labels: list[str] = []

        for held_out_index, held_out in enumerate(dataset.examples):
            training_examples = tuple(
                example
                for index, example in enumerate(dataset.examples)
                if index != held_out_index
            )
            model = ManagementStrategyKnnModel(
                k=min(self.k, len(training_examples))
            ).fit(TrainingDataset(examples=training_examples))

            actual_labels.append(held_out.best_management_strategy)
            predicted_labels.append(model.predict(held_out))

        correct_predictions = sum(
            actual == predicted
            for actual, predicted in zip(
                actual_labels,
                predicted_labels,
                strict=True,
            )
        )
        total_examples = len(actual_labels)

        labels = sorted(set(actual_labels) | set(predicted_labels))
        actual_counts = Counter(actual_labels)
        predicted_counts = Counter(predicted_labels)
        correct_counts = Counter(
            actual
            for actual, predicted in zip(
                actual_labels,
                predicted_labels,
                strict=True,
            )
            if actual == predicted
        )

        metrics = tuple(
            ManagementStrategyClassMetrics(
                label=label,
                support=actual_counts[label],
                predicted=predicted_counts[label],
                correct=correct_counts[label],
                precision=(
                    correct_counts[label] / predicted_counts[label]
                    if predicted_counts[label]
                    else 0.0
                ),
                recall=(
                    correct_counts[label] / actual_counts[label]
                    if actual_counts[label]
                    else 0.0
                ),
            )
            for label in labels
        )

        return ManagementStrategyEvaluationResult(
            total_examples=total_examples,
            correct_predictions=correct_predictions,
            accuracy=correct_predictions / total_examples,
            class_metrics=metrics,
        )
