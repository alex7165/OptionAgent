from datetime import date

import pytest

from app.analysis.management_action import ManagementAction, ThreatenedSide
from app.analysis.management_action_outcome import ManagementActionOutcome
from app.analysis.management_action_training_dataset_builder import (
    ManagementActionTrainingDatasetBuilder,
)
from app.analysis.management_decision_context import ManagementDecisionContext
from app.analysis.management_outcome_collector import ManagementOutcomeCollector


DECISION_DATE = date(2026, 7, 23)


def _outcome(action: ManagementAction, pnl: float | None) -> ManagementActionOutcome:
    return ManagementActionOutcome(
        action=action,
        threatened_side=ThreatenedSide.CALL,
        decision_date=DECISION_DATE,
        evaluation_date=date(2026, 7, 24),
        capital_required=40_000.0 if action is ManagementAction.BUY_STOCK_HEDGE else 0.0,
        maximum_drawdown=-500.0,
        total_profit_loss=pnl,
        complete_profit_loss=pnl is not None,
    )


def _context(action: ManagementAction) -> ManagementDecisionContext:
    return ManagementDecisionContext(
        decision_date=DECISION_DATE,
        trading_day_index=1,
        threatened_side=ThreatenedSide.CALL,
        action=action,
        underlying_price=568.59,
        short_strike=545.0,
        days_to_expiration=1,
        short_option_delta=0.72 if action is ManagementAction.BUY_STOCK_HEDGE else None,
        expected_move_percent=7.5,
        iv_rank=62.0,
        iv_percentile=70.0,
        entry_strategy="Short Strangle",
    )


def test_builds_one_training_row_per_action() -> None:
    collected = ManagementOutcomeCollector().collect(
        symbol="LMT",
        decision_date=DECISION_DATE,
        threatened_side=ThreatenedSide.CALL,
        outcomes=(
            _outcome(ManagementAction.CLOSE, -900.0),
            _outcome(ManagementAction.ROLL_CALL, -600.0),
            _outcome(ManagementAction.BUY_STOCK_HEDGE, None),
        ),
    )

    dataset = ManagementActionTrainingDatasetBuilder().build(
        collected,
        {
            action: _context(action)
            for action in (
                ManagementAction.CLOSE,
                ManagementAction.ROLL_CALL,
                ManagementAction.BUY_STOCK_HEDGE,
            )
        },
    )

    assert len(dataset) == 3
    rows = {row.action: row for row in dataset.examples}
    assert rows[ManagementAction.ROLL_CALL].is_best_action is True
    assert rows[ManagementAction.CLOSE].is_best_action is False
    assert rows[ManagementAction.BUY_STOCK_HEDGE].is_best_action is None
    assert rows[ManagementAction.BUY_STOCK_HEDGE].short_option_delta == 0.72
    assert rows[ManagementAction.CLOSE].entry_strategy == "short strangle"
    assert rows[ManagementAction.CLOSE].strike_distance_percent == pytest.approx(
        4.32844,
        rel=1e-5,
    )


def test_rejects_missing_action_context() -> None:
    collected = ManagementOutcomeCollector().collect(
        symbol="LMT",
        decision_date=DECISION_DATE,
        threatened_side=ThreatenedSide.CALL,
        outcomes=(_outcome(ManagementAction.CLOSE, -900.0),),
    )

    with pytest.raises(ValueError, match="missing decision context"):
        ManagementActionTrainingDatasetBuilder().build(collected, {})
