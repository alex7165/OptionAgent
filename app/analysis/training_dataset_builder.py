from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date

from app.analysis.entry_decision_snapshot import EntryDecisionSnapshot
from app.analysis.management_outcome_collection import ManagementOutcomeCollection
from app.analysis.trade_manager_advisor import ComparableManagementCase
from app.analysis.training_dataset import TrainingDataset
from app.analysis.training_example_builder import TrainingExampleBuilder


class TrainingDatasetBuilder:
    """Builds one in-memory dataset from historical management cases."""

    def __init__(
        self,
        example_builder: TrainingExampleBuilder | None = None,
    ) -> None:
        self.example_builder = example_builder or TrainingExampleBuilder()

    def build(
        self,
        *,
        entry: EntryDecisionSnapshot,
        comparable_cases: Sequence[ComparableManagementCase],
        management_outcomes: Sequence[ManagementOutcomeCollection],
        report_timing: str,
        first_reaction_move_percent_by_date: Mapping[date, float],
    ) -> TrainingDataset:
        cases_by_date = self._index_cases(comparable_cases)
        outcomes_by_date = self._index_outcomes(management_outcomes)

        case_dates = set(cases_by_date)
        outcome_dates = set(outcomes_by_date)
        reaction_dates = set(first_reaction_move_percent_by_date)

        if case_dates != outcome_dates:
            raise ValueError(
                "comparable cases and management outcomes must use the same earnings dates"
            )
        if case_dates != reaction_dates:
            raise ValueError(
                "first reaction moves must exist for every comparable earnings date"
            )

        examples = tuple(
            self.example_builder.build(
                entry=entry,
                comparable_case=cases_by_date[earnings_date],
                management_outcomes=outcomes_by_date[earnings_date],
                report_timing=report_timing,
                first_reaction_move_percent=(
                    first_reaction_move_percent_by_date[earnings_date]
                ),
            )
            for earnings_date in sorted(case_dates)
        )

        return TrainingDataset(examples=examples)

    @staticmethod
    def _index_cases(
        comparable_cases: Sequence[ComparableManagementCase],
    ) -> dict[date, ComparableManagementCase]:
        indexed: dict[date, ComparableManagementCase] = {}
        for comparable_case in comparable_cases:
            if comparable_case.report_date in indexed:
                raise ValueError("comparable case earnings dates must be unique")
            indexed[comparable_case.report_date] = comparable_case
        return indexed

    @staticmethod
    def _index_outcomes(
        management_outcomes: Sequence[ManagementOutcomeCollection],
    ) -> dict[date, ManagementOutcomeCollection]:
        indexed: dict[date, ManagementOutcomeCollection] = {}
        for collection in management_outcomes:
            if collection.earnings_date in indexed:
                raise ValueError("management outcome earnings dates must be unique")
            indexed[collection.earnings_date] = collection
        return indexed
