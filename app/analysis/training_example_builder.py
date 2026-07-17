from __future__ import annotations

from app.analysis.best_management_strategy_selector import (
    BestManagementStrategySelector,
)
from app.analysis.entry_decision_snapshot import EntryDecisionSnapshot
from app.analysis.management_outcome_collection import ManagementOutcomeCollection
from app.analysis.trade_manager_advisor import ComparableManagementCase
from app.analysis.training_example import TrainingExample


class TrainingExampleBuilder:
    """Builds one supervised training row from a comparable earnings case."""

    def __init__(
        self,
        selector: BestManagementStrategySelector | None = None,
    ) -> None:
        self.selector = selector or BestManagementStrategySelector()

    def build(
        self,
        *,
        entry: EntryDecisionSnapshot,
        comparable_case: ComparableManagementCase,
        management_outcomes: ManagementOutcomeCollection,
        report_timing: str,
        first_reaction_move_percent: float,
    ) -> TrainingExample:
        if comparable_case.report_date != management_outcomes.earnings_date:
            raise ValueError(
                "comparable case and management outcomes must use the same earnings date"
            )
        if entry.symbol.strip().upper() != management_outcomes.symbol:
            raise ValueError(
                "entry and management outcomes must use the same symbol"
            )

        best_outcome = self.selector.select_best(management_outcomes.outcomes)
        reference_price = management_outcomes.reference_price

        return TrainingExample(
            symbol=management_outcomes.symbol,
            earnings_date=management_outcomes.earnings_date,
            report_timing=report_timing,
            reference_price=reference_price,
            entry_strategy=entry.strategy.value,
            expected_move_percent=entry.expected_move_percent,
            short_put_distance_percent=(
                entry.short_put_strike / entry.reference_price - 1
            )
            * 100,
            short_call_distance_percent=(
                entry.short_call_strike / entry.reference_price - 1
            )
            * 100,
            first_reaction_move_percent=first_reaction_move_percent,
            maximum_move_percent=comparable_case.maximum_move_percent,
            friday_close_move_percent=comparable_case.friday_close_move_percent,
            made_all_time_high=comparable_case.made_all_time_high,
            best_management_strategy=best_outcome.strategy_name,
        )
