from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.analysis.management_outcome import ManagementOutcome


@dataclass(frozen=True, slots=True)
class ManagementStrategyScore:
    """Deterministic training label derived from a management outcome."""

    success_score: float
    risk_score: float
    reward_score: float
    overall_score: float

    @classmethod
    def from_outcome(
        cls,
        outcome: ManagementOutcome,
    ) -> ManagementStrategyScore:
        success_score = 100.0 if outcome.finished_inside_strikes else 0.0
        risk_score = _clamp(abs(min(outcome.max_adverse_move, 0.0)) * 10.0)
        reward_score = _clamp(max(outcome.max_favorable_move, 0.0) * 10.0)

        holding_days = max(outcome.exit_day - outcome.entry_day, 0)
        time_penalty = min(holding_days * 2.5, 10.0)
        overall_score = _clamp(
            success_score * 0.60
            + (100.0 - risk_score) * 0.25
            + reward_score * 0.15
            - time_penalty
        )

        return cls(
            success_score=success_score,
            risk_score=risk_score,
            reward_score=reward_score,
            overall_score=overall_score,
        )


def _clamp(value: float) -> float:
    return max(0.0, min(value, 100.0))
