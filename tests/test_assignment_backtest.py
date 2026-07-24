from datetime import date

import pytest

from app.analysis.assignment_backtest import AssignmentBacktestAnalyzer, CoveredCallSale
from app.analysis.management_action import ManagementAction, ThreatenedSide
from app.analysis.management_decision_context import ManagementDecisionContext
from app.marketdata.price_history_provider import DailyBar


def context() -> ManagementDecisionContext:
    return ManagementDecisionContext(
        decision_date=date(2026, 7, 24),
        trading_day_index=2,
        threatened_side=ThreatenedSide.PUT,
        action=ManagementAction.ASSIGN_AND_SELL_COVERED_CALL,
        underlying_price=11.02,
        short_strike=13.50,
        days_to_expiration=0,
    )


def bar(day: int, low: float, high: float, close: float) -> DailyBar:
    return DailyBar(
        date=date(2026, 7, day),
        open=11.02,
        high=high,
        low=low,
        close=close,
        volume=1000,
    )


def test_assignment_uses_explicit_covered_call_premium() -> None:
    outcome = AssignmentBacktestAnalyzer().analyze(
        context(),
        (
            bar(24, 10.80, 11.30, 11.02),
            bar(31, 10.90, 13.20, 13.10),
        ),
        put_premium_per_share=0.55,
        covered_call_sales=(
            CoveredCallSale(
                sale_date=date(2026, 7, 27),
                expiration_date=date(2026, 7, 31),
                strike=12.50,
                premium_per_share=0.35,
                delta=0.25,
            ),
        ),
    )

    assert outcome.covered_call_premium_total == 35.0
    assert outcome.shares_called_away is True
    assert outcome.total_profit_loss == pytest.approx(-10.0)


def test_assignment_without_call_marks_stock_to_market() -> None:
    outcome = AssignmentBacktestAnalyzer().analyze(
        context(),
        (
            bar(24, 10.80, 11.30, 11.02),
            bar(31, 10.50, 12.00, 11.80),
        ),
        put_premium_per_share=0.55,
    )

    assert outcome.effective_cost_basis_per_share == pytest.approx(12.95)
    assert outcome.total_profit_loss == pytest.approx(-115.0)
    assert outcome.shares_called_away is False
