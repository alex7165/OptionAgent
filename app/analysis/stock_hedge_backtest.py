from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math

from app.analysis.management_action import ManagementAction, ThreatenedSide
from app.analysis.management_decision_context import ManagementDecisionContext
from app.marketdata.price_history_provider import DailyBar


@dataclass(frozen=True, slots=True)
class StockHedgeBacktestOutcome:
    """Observable stock leg of a delta hedge for a threatened short call.

    Historical option prices are not part of the current training data. The
    outcome therefore reports the stock hedge separately and never presents it
    as total repaired-position P/L.
    """

    action: ManagementAction
    decision_date: date
    exit_date: date
    contracts: int
    short_call_delta: float
    short_put_delta: float | None
    net_short_option_delta_shares: float
    target_stock_shares: int
    existing_stock_shares: int
    shares_bought: int
    entry_price: float
    exit_price: float
    capital_required: float
    stock_profit_loss: float
    maximum_stock_drawdown: float
    maximum_stock_drawdown_percent: float
    maximum_stock_gain: float
    maximum_stock_gain_percent: float
    option_profit_loss_available: bool
    observations: tuple[str, ...]


class StockHedgeBacktestAnalyzer:
    """Backtest the long-stock component of a short-call delta hedge."""

    def analyze(
        self,
        context: ManagementDecisionContext,
        daily_bars: tuple[DailyBar, ...],
        *,
        contracts: int = 1,
        short_put_delta: float | None = None,
        existing_stock_shares: int = 0,
        hedge_ratio: float = 1.0,
    ) -> StockHedgeBacktestOutcome:
        self._validate(
            context=context,
            daily_bars=daily_bars,
            contracts=contracts,
            short_put_delta=short_put_delta,
            existing_stock_shares=existing_stock_shares,
            hedge_ratio=hedge_ratio,
        )

        short_call_delta = abs(context.short_option_delta or 0.0)
        effective_put_delta = short_put_delta or 0.0

        # Deltas supplied by providers are long-option deltas. A short call has
        # the opposite delta; a long-stock hedge offsets the complete short
        # option position. The negative put delta reduces the required shares.
        net_long_option_delta = short_call_delta + effective_put_delta
        net_short_option_delta_shares = -net_long_option_delta * 100 * contracts
        target_shares = max(
            0,
            round(-net_short_option_delta_shares * hedge_ratio),
        )
        shares_bought = max(0, target_shares - existing_stock_shares)

        entry_price = context.underlying_price
        exit_bar = daily_bars[-1]
        capital_required = shares_bought * entry_price
        stock_profit_loss = shares_bought * (exit_bar.close - entry_price)

        lowest_price = min(entry_price, *(bar.low for bar in daily_bars))
        highest_price = max(entry_price, *(bar.high for bar in daily_bars))
        max_drawdown = shares_bought * (lowest_price - entry_price)
        max_gain = shares_bought * (highest_price - entry_price)

        return StockHedgeBacktestOutcome(
            action=ManagementAction.BUY_STOCK_HEDGE,
            decision_date=context.decision_date,
            exit_date=exit_bar.date,
            contracts=contracts,
            short_call_delta=short_call_delta,
            short_put_delta=short_put_delta,
            net_short_option_delta_shares=net_short_option_delta_shares,
            target_stock_shares=target_shares,
            existing_stock_shares=existing_stock_shares,
            shares_bought=shares_bought,
            entry_price=entry_price,
            exit_price=exit_bar.close,
            capital_required=capital_required,
            stock_profit_loss=stock_profit_loss,
            maximum_stock_drawdown=max_drawdown,
            maximum_stock_drawdown_percent=(lowest_price / entry_price - 1) * 100,
            maximum_stock_gain=max_gain,
            maximum_stock_gain_percent=(highest_price / entry_price - 1) * 100,
            option_profit_loss_available=False,
            observations=(
                "Aktienhedge aus dem Netto-Delta der Short-Optionen berechnet.",
                "Historische Optionspreise fehlen; ausgewiesen wird nur das P/L der zusätzlich gekauften Aktien.",
                "Der Hedge wird am Ende des letzten übergebenen Handelstags aufgelöst.",
            ),
        )

    @staticmethod
    def _validate(
        *,
        context: ManagementDecisionContext,
        daily_bars: tuple[DailyBar, ...],
        contracts: int,
        short_put_delta: float | None,
        existing_stock_shares: int,
        hedge_ratio: float,
    ) -> None:
        if context.action is not ManagementAction.BUY_STOCK_HEDGE:
            raise ValueError("context action must be buy_stock_hedge")
        if context.threatened_side is not ThreatenedSide.CALL:
            raise ValueError("stock hedge is only valid for threatened call side")
        if context.short_option_delta is None:
            raise ValueError("short call delta is required")
        if contracts <= 0:
            raise ValueError("contracts must be greater than zero")
        if existing_stock_shares < 0:
            raise ValueError("existing_stock_shares must not be negative")
        if not 0 < hedge_ratio <= 1:
            raise ValueError("hedge_ratio must be greater than zero and at most one")
        if short_put_delta is not None and not -1 <= short_put_delta <= 0:
            raise ValueError("short_put_delta must be between -1 and zero")
        if not daily_bars:
            raise ValueError("daily_bars must not be empty")
        if any(
            not math.isfinite(value) or value <= 0
            for bar in daily_bars
            for value in (bar.open, bar.high, bar.low, bar.close)
        ):
            raise ValueError("daily bar prices must be finite and greater than zero")
        if any(bar.date < context.decision_date for bar in daily_bars):
            raise ValueError("daily_bars must not contain dates before decision_date")
        if any(
            current.date >= following.date
            for current, following in zip(daily_bars, daily_bars[1:])
        ):
            raise ValueError("daily_bars must be ordered by ascending unique date")
