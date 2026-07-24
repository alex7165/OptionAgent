from datetime import date

import pytest

from app.analysis.assignment_backtest import (
    AssignmentBacktestAnalyzer,
    CoveredCallSale,
)
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


def test_assignment_without_historical_calls_marks_stock_to_market() -> None:
    outcome = AssignmentBacktestAnalyzer().analyze(
        context(),
        (
            bar(24, low=10.80, high=11.30, close=11.02),
            bar(31, low=10.50, high=12.00, close=11.80),
        ),
        put_premium_per_share=0.55,
    )

    assert outcome.shares_assigned == 100
    assert outcome.effective_cost_basis_per_share == pytest.approx(12.95)
    assert outcome.capital_required == 1350.0
    assert outcome.stock_profit_loss == pytest.approx(-170.0)
    assert outcome.total_profit_loss == pytest.approx(-115.0)
    assert outcome.maximum_drawdown == pytest.approx(-245.0)
    assert outcome.historical_covered_call_prices_available is False
    assert outcome.shares_called_away is False


def test_covered_call_premium_and_call_away_are_included() -> None:
    outcome = AssignmentBacktestAnalyzer().analyze(
        context(),
        (
            bar(24, low=10.80, high=11.30, close=11.02),
            bar(31, low=10.90, high=13.20, close=13.10),
        ),
        put_premium_per_share=0.55,
        roll_credit_per_share=0.10,
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

    assert outcome.covered_calls_sold == 1
    assert outcome.covered_call_premium_total == 35.0
    assert outcome.shares_called_away is True
    assert outcome.called_away_price == 12.50
    assert outcome.stock_profit_loss == pytest.approx(-100.0)
    assert outcome.total_profit_loss == pytest.approx(0.0)


def test_covered_call_not_exercised_when_expiration_close_below_strike() -> None:
    outcome = AssignmentBacktestAnalyzer().analyze(
        context(),
        (
            bar(24, low=10.80, high=11.30, close=11.02),
            bar(31, low=10.90, high=12.80, close=12.40),
        ),
        covered_call_sales=(
            CoveredCallSale(
                sale_date=date(2026, 7, 27),
                expiration_date=date(2026, 7, 31),
                strike=12.50,
                premium_per_share=0.25,
            ),
        ),
    )

    assert outcome.shares_called_away is False
    assert outcome.ending_stock_price == 12.40
    assert outcome.total_profit_loss == pytest.approx(-85.0)


def test_rejects_call_side_assignment() -> None:
    invalid_context = ManagementDecisionContext(
        decision_date=date(2026, 7, 24),
        trading_day_index=1,
        threatened_side=ThreatenedSide.CALL,
        action=ManagementAction.CLOSE,
        underlying_price=100.0,
        short_strike=95.0,
        days_to_expiration=0,
    )

    with pytest.raises(ValueError, match="context action"):
        AssignmentBacktestAnalyzer().analyze(
            invalid_context,
            (bar(24, low=10.0, high=12.0, close=11.0),),
        )


def test_rejects_overlapping_covered_calls() -> None:
    sales = (
        CoveredCallSale(
            sale_date=date(2026, 7, 27),
            expiration_date=date(2026, 7, 31),
            strike=12.0,
            premium_per_share=0.20,
        ),
        CoveredCallSale(
            sale_date=date(2026, 7, 31),
            expiration_date=date(2026, 8, 7),
            strike=12.5,
            premium_per_share=0.25,
        ),
    )

    with pytest.raises(ValueError, match="must not overlap"):
        AssignmentBacktestAnalyzer().analyze(
            context(),
            (
                bar(24, low=10.0, high=12.0, close=11.0),
                bar(31, low=10.0, high=12.0, close=11.0),
            ),
            covered_call_sales=sales,
        )
