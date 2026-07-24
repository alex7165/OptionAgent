from datetime import date

import pytest

from app.analysis.management_action import ManagementAction, ThreatenedSide
from app.analysis.management_decision_context import ManagementDecisionContext


def test_calculates_call_stock_hedge_from_delta() -> None:
    context = ManagementDecisionContext(
        decision_date=date(2026, 7, 23),
        trading_day_index=1,
        threatened_side=ThreatenedSide.CALL,
        action=ManagementAction.BUY_STOCK_HEDGE,
        underlying_price=568.59,
        short_strike=545.0,
        days_to_expiration=1,
        short_option_delta=0.72,
    )

    assert context.stock_hedge_shares_per_contract == 72


def test_accepts_assignment_and_covered_call_for_put_side() -> None:
    context = ManagementDecisionContext(
        decision_date=date(2026, 7, 23),
        trading_day_index=1,
        threatened_side=ThreatenedSide.PUT,
        action=ManagementAction.ASSIGN_AND_SELL_COVERED_CALL,
        underlying_price=11.44,
        short_strike=13.5,
        days_to_expiration=1,
    )

    assert context.action is ManagementAction.ASSIGN_AND_SELL_COVERED_CALL


def test_rejects_stock_hedge_for_put_side() -> None:
    with pytest.raises(ValueError, match="not valid for put side"):
        ManagementDecisionContext(
            decision_date=date(2026, 7, 23),
            trading_day_index=1,
            threatened_side=ThreatenedSide.PUT,
            action=ManagementAction.BUY_STOCK_HEDGE,
            underlying_price=11.44,
            short_strike=13.5,
            days_to_expiration=1,
            short_option_delta=0.70,
        )


def test_rejects_assignment_action_for_call_side() -> None:
    with pytest.raises(ValueError, match="not valid for call side"):
        ManagementDecisionContext(
            decision_date=date(2026, 7, 23),
            trading_day_index=1,
            threatened_side=ThreatenedSide.CALL,
            action=ManagementAction.HOLD_FOR_ASSIGNMENT,
            underlying_price=568.59,
            short_strike=545.0,
            days_to_expiration=1,
        )
