from datetime import date

import pytest

from app.analysis.management_action import ManagementAction, ThreatenedSide
from app.analysis.management_decision_context import ManagementDecisionContext
from app.analysis.stock_hedge_backtest import StockHedgeBacktestAnalyzer
from app.marketdata.price_history_provider import DailyBar


def context(delta: float = 0.72, price: float = 568.59) -> ManagementDecisionContext:
    return ManagementDecisionContext(
        decision_date=date(2026, 7, 23),
        trading_day_index=1,
        threatened_side=ThreatenedSide.CALL,
        action=ManagementAction.BUY_STOCK_HEDGE,
        underlying_price=price,
        short_strike=545.0,
        days_to_expiration=1,
        short_option_delta=delta,
    )


def bar(day: int, low: float, high: float, close: float) -> DailyBar:
    return DailyBar(
        date=date(2026, 7, day),
        open=568.59,
        high=high,
        low=low,
        close=close,
        volume=1000,
    )


def test_backtests_call_delta_stock_hedge_until_last_bar() -> None:
    outcome = StockHedgeBacktestAnalyzer().analyze(
        context(),
        (
            bar(23, low=565.0, high=575.0, close=570.0),
            bar(24, low=560.0, high=580.0, close=578.99),
        ),
    )

    assert outcome.target_stock_shares == 72
    assert outcome.shares_bought == 72
    assert outcome.capital_required == pytest.approx(40938.48)
    assert outcome.stock_profit_loss == pytest.approx(748.8)
    assert outcome.maximum_stock_drawdown == pytest.approx(-618.48)
    assert outcome.maximum_stock_gain == pytest.approx(821.52)
    assert outcome.option_profit_loss_available is False


def test_put_delta_reduces_required_stock_hedge_for_short_strangle() -> None:
    outcome = StockHedgeBacktestAnalyzer().analyze(
        context(delta=0.80, price=100.0),
        (bar(23, low=99.0, high=105.0, close=104.0),),
        contracts=2,
        short_put_delta=-0.15,
    )

    assert outcome.net_short_option_delta_shares == pytest.approx(-130.0)
    assert outcome.target_stock_shares == 130
    assert outcome.shares_bought == 130


def test_partial_hedge_and_existing_shares_only_buy_difference() -> None:
    outcome = StockHedgeBacktestAnalyzer().analyze(
        context(delta=0.80, price=100.0),
        (bar(23, low=98.0, high=104.0, close=102.0),),
        existing_stock_shares=20,
        hedge_ratio=0.5,
    )

    assert outcome.target_stock_shares == 40
    assert outcome.shares_bought == 20
    assert outcome.capital_required == 2000.0
    assert outcome.stock_profit_loss == 40.0


def test_rejects_invalid_put_delta() -> None:
    with pytest.raises(ValueError, match="short_put_delta"):
        StockHedgeBacktestAnalyzer().analyze(
            context(),
            (bar(23, low=565.0, high=575.0, close=570.0),),
            short_put_delta=0.20,
        )
