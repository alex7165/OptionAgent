from datetime import date

import pytest

from app.analysis.management_action import ManagementAction, ThreatenedSide
from app.analysis.management_action_outcome import ManagementActionOutcome
from app.analysis.management_outcome_collector import ManagementOutcomeCollector


DECISION_DATE = date(2026, 7, 23)


def _outcome(
    action: ManagementAction,
    profit_loss: float | None,
    *,
    drawdown: float = -100.0,
    capital: float = 0.0,
) -> ManagementActionOutcome:
    return ManagementActionOutcome(
        action=action,
        threatened_side=ThreatenedSide.CALL,
        decision_date=DECISION_DATE,
        evaluation_date=date(2026, 7, 24),
        capital_required=capital,
        maximum_drawdown=drawdown,
        total_profit_loss=profit_loss,
        complete_profit_loss=profit_loss is not None,
    )


def test_collector_selects_best_only_from_complete_profit_loss() -> None:
    result = ManagementOutcomeCollector().collect(
        symbol=" lmt ",
        decision_date=DECISION_DATE,
        threatened_side=ThreatenedSide.CALL,
        outcomes=(
            _outcome(ManagementAction.CLOSE, -900.0),
            _outcome(ManagementAction.ROLL_CALL, -600.0),
            _outcome(ManagementAction.BUY_STOCK_HEDGE, None, capital=40_000.0),
        ),
    )

    assert result.symbol == "LMT"
    assert result.best_action is ManagementAction.ROLL_CALL
    assert result.best_action_profit_loss == -600.0
    assert result.incomplete_actions == (ManagementAction.BUY_STOCK_HEDGE,)


def test_collector_does_not_create_label_when_all_outcomes_are_incomplete() -> None:
    result = ManagementOutcomeCollector().collect(
        symbol="LMT",
        decision_date=DECISION_DATE,
        threatened_side=ThreatenedSide.CALL,
        outcomes=(
            _outcome(ManagementAction.BUY_STOCK_HEDGE, None),
        ),
    )

    assert result.best_action is None
    assert result.best_action_profit_loss is None


def test_collector_rejects_duplicate_actions() -> None:
    with pytest.raises(ValueError, match="duplicate outcome"):
        ManagementOutcomeCollector().collect(
            symbol="LMT",
            decision_date=DECISION_DATE,
            threatened_side=ThreatenedSide.CALL,
            outcomes=(
                _outcome(ManagementAction.CLOSE, -900.0),
                _outcome(ManagementAction.CLOSE, -800.0),
            ),
        )
