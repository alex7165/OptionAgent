from datetime import date

import pytest

from app.analysis.entry_decision_snapshot import EntryDecisionSnapshot
from app.analysis.management_outcome import ManagementOutcome
from app.analysis.management_outcome_collection import ManagementOutcomeCollection
from app.analysis.management_strategy_score import ManagementStrategyScore
from app.analysis.strategy import Strategy
from app.analysis.trade_manager_advisor import ComparableManagementCase
from app.analysis.training_dataset_builder import TrainingDatasetBuilder


def _entry() -> EntryDecisionSnapshot:
    return EntryDecisionSnapshot(
        symbol="GS",
        decision_date=date(2026, 7, 13),
        report_date=date(2026, 7, 14),
        expiration=date(2026, 7, 17),
        strategy=Strategy.SHORT_STRANGLE,
        reference_price=100.0,
        short_put_strike=92.0,
        short_call_strike=110.0,
        expected_move_percent=8.4,
    )


def _case(report_date: date, friday_move: float) -> ComparableManagementCase:
    return ComparableManagementCase(
        report_date=report_date,
        maximum_move_percent=abs(friday_move) + 2.0,
        maximum_move_trading_day=2,
        friday_close_move_percent=friday_move,
        made_all_time_high=friday_move > 0,
    )


def _outcome(strategy_name: str, overall_score: float) -> ManagementOutcome:
    return ManagementOutcome(
        strategy_name=strategy_name,
        entry_day=1,
        exit_day=1,
        exit_reason="test",
        max_adverse_move=-1.0,
        max_favorable_move=2.0,
        finished_inside_strikes=True,
        all_time_high_after_entry=False,
        final_move_percent=1.0,
        score=ManagementStrategyScore(
            success_score=100.0,
            risk_score=10.0,
            reward_score=20.0,
            overall_score=overall_score,
        ),
    )


def _collection(report_date: date) -> ManagementOutcomeCollection:
    return ManagementOutcomeCollection(
        symbol="GS",
        earnings_date=report_date,
        reference_price=95.0,
        outcomes=(
            _outcome("close_day1", 70.0),
            _outcome("hold_until_friday", 80.0),
        ),
    )


def test_builds_one_training_example_per_historical_case() -> None:
    first_date = date(2023, 7, 17)
    second_date = date(2024, 7, 15)

    dataset = TrainingDatasetBuilder().build(
        entry=_entry(),
        comparable_cases=(
            _case(second_date, 7.0),
            _case(first_date, -3.0),
        ),
        management_outcomes=(
            _collection(second_date),
            _collection(first_date),
        ),
        report_timing="AMC",
        first_reaction_move_percent_by_date={
            second_date: 10.1,
            first_date: -5.2,
        },
    )

    assert len(dataset) == 2
    assert tuple(example.earnings_date for example in dataset.examples) == (
        first_date,
        second_date,
    )
    assert tuple(
        example.first_reaction_move_percent for example in dataset.examples
    ) == (-5.2, 10.1)
    assert all(
        example.best_management_strategy == "hold_until_friday"
        for example in dataset.examples
    )


def test_builds_empty_dataset_from_empty_inputs() -> None:
    dataset = TrainingDatasetBuilder().build(
        entry=_entry(),
        comparable_cases=(),
        management_outcomes=(),
        report_timing="AMC",
        first_reaction_move_percent_by_date={},
    )

    assert len(dataset) == 0
    assert dataset.examples == ()


def test_rejects_incomplete_management_outcomes() -> None:
    report_date = date(2024, 7, 15)

    with pytest.raises(ValueError, match="same earnings dates"):
        TrainingDatasetBuilder().build(
            entry=_entry(),
            comparable_cases=(_case(report_date, 7.0),),
            management_outcomes=(),
            report_timing="AMC",
            first_reaction_move_percent_by_date={report_date: 10.1},
        )
