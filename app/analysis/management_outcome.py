from __future__ import annotations

from dataclasses import dataclass

from app.analysis.management_strategy_score import ManagementStrategyScore


@dataclass(frozen=True, slots=True)
class ManagementOutcome:
    """Standardized result of one historical trade-management simulation."""

    strategy_name: str
    entry_day: int
    exit_day: int
    exit_reason: str
    max_adverse_move: float
    max_favorable_move: float
    finished_inside_strikes: bool
    all_time_high_after_entry: bool
    final_move_percent: float
    score: ManagementStrategyScore | None = None
