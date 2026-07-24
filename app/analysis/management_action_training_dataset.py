from __future__ import annotations

from dataclasses import dataclass

from app.analysis.management_action_training_example import (
    ManagementActionTrainingExample,
)


@dataclass(frozen=True, slots=True)
class ManagementActionTrainingDataset:
    """Action-level dataset: one row per situation and candidate action."""

    examples: tuple[ManagementActionTrainingExample, ...]

    def __len__(self) -> int:
        return len(self.examples)
