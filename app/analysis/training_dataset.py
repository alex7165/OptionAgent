from __future__ import annotations

from dataclasses import dataclass

from app.analysis.training_example import TrainingExample


@dataclass(frozen=True, slots=True)
class TrainingDataset:
    """In-memory collection of supervised management training examples."""

    examples: tuple[TrainingExample, ...]

    def __len__(self) -> int:
        return len(self.examples)
