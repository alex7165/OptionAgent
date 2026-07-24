from datetime import date

import pytest

from app.analysis.assignment_backtest import AssignmentBacktestOutcome
from app.analysis.management_action import ManagementAction, ThreatenedSide
from app.analysis.management_action_outcome import ManagementActionOutcome
from app.analysis.stock_hedge_backtest import StockHedgeBacktestOutcome


def test_stock_hedge_adapter_does_not_invent_total_profit_loss() -> None:
    source = StockHedgeBacktestOutcome(
        action=ManagementAction.BUY_STOCK_HEDGE,
        decision_date=date(2026, 7, 23),
        exit_date=date(2026, 7, 24),
        contracts=1,
        short_call_delta=0.72,
        short_put_delta=None,
        net_short_option_delta_shares=-72.0,
        target_stock_shares=72,
        existing_stock_shares=0,
        shares_bought=72,
        entry_price=100.0,
        exit_price=105.0,
        capital_required=7200.0,
        stock_profit_loss=360.0,
        maximum_stock_drawdown=-144.0,
        maximum_stock_drawdown_percent=-2.0,
        maximum_stock_gain=432.0,
        maximum_stock_gain_percent=6.0,
        option_profit_loss_available=False,
        observations=("stock leg only",),
    )

    outcome = ManagementActionOutcome.from_stock_hedge(source)

    assert outcome.total_profit_loss is None
    assert outcome.complete_profit_loss is False
    assert outcome.capital_required == 7200.0
    assert outcome.maximum_drawdown == -144.0


def test_assignment_adapter_exposes_complete_total_profit_loss() -> None:
    source = AssignmentBacktestOutcome(
        action=ManagementAction.ASSIGN_AND_SELL_COVERED_CALL,
        assignment_date=date(2026, 7, 24),
        evaluation_date=date(2026, 8, 7),
        contracts=1,
        shares_assigned=100,
        put_strike=50.0,
        put_premium_per_share=2.0,
        roll_credit_per_share=0.0,
        effective_cost_basis_per_share=48.0,
        capital_required=5000.0,
        covered_calls_sold=1,
        covered_call_premium_total=100.0,
        shares_called_away=True,
        called_away_date=date(2026, 8, 7),
        called_away_price=50.0,
        ending_stock_price=50.0,
        stock_profit_loss=0.0,
        total_profit_loss=300.0,
        maximum_drawdown=-500.0,
        maximum_drawdown_percent=-10.4167,
    )

    outcome = ManagementActionOutcome.from_assignment(source)

    assert outcome.threatened_side is ThreatenedSide.PUT
    assert outcome.total_profit_loss == 300.0
    assert outcome.complete_profit_loss is True


def test_profit_loss_completeness_must_be_consistent() -> None:
    with pytest.raises(ValueError, match="must match"):
        ManagementActionOutcome(
            action=ManagementAction.CLOSE,
            threatened_side=ThreatenedSide.CALL,
            decision_date=date(2026, 7, 23),
            evaluation_date=date(2026, 7, 23),
            capital_required=0.0,
            maximum_drawdown=0.0,
            total_profit_loss=None,
            complete_profit_loss=True,
        )
