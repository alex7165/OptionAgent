from datetime import date

import pytest

from app.analysis.entry_decision_snapshot import EntryDecisionSnapshot
from app.analysis.management_outcome import ManagementOutcome
from app.analysis.management_outcome_collection import ManagementOutcomeCollection
from app.analysis.management_strategy_score import ManagementStrategyScore
from app.analysis.strategy import Strategy
from app.analysis.trade_manager_advisor import ComparableManagementCase
from app.analysis.training_example_builder import TrainingExampleBuilder


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


def _entry() -> EntryDecisionSnapshot:
    return EntryDecisionSnapshot(
        symbol="gs",
        decision_date=date(2026, 7, 13),
        report_date=date(2026, 7, 14),
        expiration=date(2026, 7, 17),
        strategy=Strategy.SHORT_STRANGLE,
        reference_price=100.0,
        short_put_strike=92.0,
        short_call_strike=110.0,
        expected_move_percent=8.4,
    )


def _case() -> ComparableManagementCase:
    return ComparableManagementCase(
        report_date=date(2024, 7, 15),
        maximum_move_percent=12.5,
        maximum_move_trading_day=2,
        friday_close_move_percent=7.0,
        made_all_time_high=True,
    )


def _collection() -> ManagementOutcomeCollection:
    return ManagementOutcomeCollection(
        symbol="GS",
        earnings_date=date(2024, 7, 15),
        reference_price=95.0,
        outcomes=(
            _outcome("close_day1", 72.0),
            _outcome("hold_until_friday", 84.0),
        ),
    )


def test_builds_training_example_with_best_strategy_label() -> None:
    example = TrainingExampleBuilder().build(
        entry=_entry(),
        comparable_case=_case(),
        management_outcomes=_collection(),
        report_timing="AMC",
        first_reaction_move_percent=10.1,
    )

    assert example.symbol == "GS"
    assert example.earnings_date == date(2024, 7, 15)
    assert example.report_timing == "amc"
    assert example.reference_price == 95.0
    assert example.entry_strategy == "Short Strangle"
    assert example.expected_move_percent == 8.4
    assert example.short_put_distance_percent == pytest.approx(-8.0)
    assert example.short_call_distance_percent == pytest.approx(10.0)
    assert example.first_reaction_move_percent == 10.1
    assert example.maximum_move_percent == 12.5
    assert example.friday_close_move_percent == 7.0
    assert example.made_all_time_high is True
    assert example.best_management_strategy == "hold_until_friday"


def test_rejects_mismatched_earnings_dates() -> None:
    collection = ManagementOutcomeCollection(
        symbol="GS",
        earnings_date=date(2024, 7, 16),
        reference_price=95.0,
        outcomes=(_outcome("close_day1", 72.0),),
    )

    with pytest.raises(ValueError, match="same earnings date"):
        TrainingExampleBuilder().build(
            entry=_entry(),
            comparable_case=_case(),
            management_outcomes=collection,
            report_timing="AMC",
            first_reaction_move_percent=10.1,
        )


def test_rejects_mismatched_symbols() -> None:
    collection = ManagementOutcomeCollection(
        symbol="JPM",
        earnings_date=date(2024, 7, 15),
        reference_price=95.0,
        outcomes=(_outcome("close_day1", 72.0),),
    )

    with pytest.raises(ValueError, match="same symbol"):
        TrainingExampleBuilder().build(
            entry=_entry(),
            comparable_case=_case(),
            management_outcomes=collection,
            report_timing="AMC",
            first_reaction_move_percent=10.1,
        )
