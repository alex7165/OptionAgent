from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math

from app.analysis.management_action import ManagementAction, ThreatenedSide
from app.analysis.management_decision_context import ManagementDecisionContext
from app.marketdata.price_history_provider import DailyBar


@dataclass(frozen=True, slots=True)
class CoveredCallSale:
    """Historical covered-call sale supplied to the assignment simulation.

    Premiums and strikes must come from an actual historical option-chain
    source. The backtest deliberately does not estimate unavailable premiums.
    """

    sale_date: date
    expiration_date: date
    strike: float
    premium_per_share: float
    delta: float | None = None

    def __post_init__(self) -> None:
        if self.expiration_date < self.sale_date:
            raise ValueError("expiration_date must not be before sale_date")
        if not math.isfinite(self.strike) or self.strike <= 0:
            raise ValueError("strike must be finite and greater than zero")
        if not math.isfinite(self.premium_per_share) or self.premium_per_share < 0:
            raise ValueError(
                "premium_per_share must be finite and must not be negative"
            )
        if self.delta is not None and not 0 <= self.delta <= 1:
            raise ValueError("delta must be between zero and one")


@dataclass(frozen=True, slots=True)
class AssignmentBacktestOutcome:
    action: ManagementAction
    assignment_date: date
    evaluation_date: date
    contracts: int
    shares_assigned: int
    put_strike: float
    put_premium_per_share: float
    roll_credit_per_share: float
    effective_cost_basis_per_share: float
    capital_required: float
    covered_calls_sold: int
    covered_call_premium_total: float
    shares_called_away: bool
    called_away_date: date | None
    called_away_price: float | None
    ending_stock_price: float
    stock_profit_loss: float
    total_profit_loss: float
    maximum_drawdown: float
    maximum_drawdown_percent: float
    historical_covered_call_prices_available: bool
    observations: tuple[str, ...]


class AssignmentBacktestAnalyzer:
    """Backtest assignment plus optional covered calls on the assigned shares.

    The put is assumed to be assigned at its strike. Covered-call premiums are
    only included when explicit historical sales are passed in. Exercise is
    evaluated at expiration using the underlying close; early assignment is
    intentionally outside this first version.
    """

    def analyze(
        self,
        context: ManagementDecisionContext,
        daily_bars: tuple[DailyBar, ...],
        *,
        contracts: int = 1,
        put_premium_per_share: float = 0.0,
        roll_credit_per_share: float = 0.0,
        covered_call_sales: tuple[CoveredCallSale, ...] = (),
    ) -> AssignmentBacktestOutcome:
        self._validate(
            context=context,
            daily_bars=daily_bars,
            contracts=contracts,
            put_premium_per_share=put_premium_per_share,
            roll_credit_per_share=roll_credit_per_share,
            covered_call_sales=covered_call_sales,
        )

        shares = contracts * 100
        cost_basis = (
            context.short_strike
            - put_premium_per_share
            - roll_credit_per_share
        )
        if cost_basis <= 0:
            raise ValueError("effective cost basis must be greater than zero")

        bars_by_date = {bar.date: bar for bar in daily_bars}
        premium_total = sum(
            sale.premium_per_share * shares for sale in covered_call_sales
        )

        shares_called_away = False
        called_away_date: date | None = None
        called_away_price: float | None = None

        for sale in covered_call_sales:
            expiration_bar = bars_by_date.get(sale.expiration_date)
            if expiration_bar is None:
                raise ValueError(
                    "daily_bars must contain every covered-call expiration date"
                )
            if expiration_bar.close >= sale.strike:
                shares_called_away = True
                called_away_date = sale.expiration_date
                called_away_price = sale.strike
                break

        evaluation_bar = (
            bars_by_date[called_away_date]
            if called_away_date is not None
            else daily_bars[-1]
        )
        ending_price = called_away_price or evaluation_bar.close
        stock_profit_loss = shares * (ending_price - context.short_strike)
        original_put_credit = shares * put_premium_per_share
        roll_credit = shares * roll_credit_per_share
        total_profit_loss = (
            stock_profit_loss
            + original_put_credit
            + roll_credit
            + premium_total
        )

        relevant_bars = tuple(
            bar for bar in daily_bars if bar.date <= evaluation_bar.date
        )
        lowest_price = min(bar.low for bar in relevant_bars)
        maximum_drawdown = shares * (lowest_price - cost_basis)

        return AssignmentBacktestOutcome(
            action=ManagementAction.ASSIGN_AND_SELL_COVERED_CALL,
            assignment_date=context.decision_date,
            evaluation_date=evaluation_bar.date,
            contracts=contracts,
            shares_assigned=shares,
            put_strike=context.short_strike,
            put_premium_per_share=put_premium_per_share,
            roll_credit_per_share=roll_credit_per_share,
            effective_cost_basis_per_share=cost_basis,
            capital_required=shares * context.short_strike,
            covered_calls_sold=len(covered_call_sales),
            covered_call_premium_total=premium_total,
            shares_called_away=shares_called_away,
            called_away_date=called_away_date,
            called_away_price=called_away_price,
            ending_stock_price=ending_price,
            stock_profit_loss=stock_profit_loss,
            total_profit_loss=total_profit_loss,
            maximum_drawdown=maximum_drawdown,
            maximum_drawdown_percent=(lowest_price / cost_basis - 1) * 100,
            historical_covered_call_prices_available=bool(covered_call_sales),
            observations=(
                "Andienung wird mit 100 Aktien je Short Put simuliert.",
                "Covered-Call-Prämien werden nur aus explizit übergebenen historischen Optionsdaten verwendet.",
                "Ausübung des Covered Calls wird am Verfall anhand des Schlusskurses geprüft; frühe Ausübung ist noch nicht enthalten.",
            ),
        )

    @staticmethod
    def _validate(
        *,
        context: ManagementDecisionContext,
        daily_bars: tuple[DailyBar, ...],
        contracts: int,
        put_premium_per_share: float,
        roll_credit_per_share: float,
        covered_call_sales: tuple[CoveredCallSale, ...],
    ) -> None:
        if context.action is not ManagementAction.ASSIGN_AND_SELL_COVERED_CALL:
            raise ValueError(
                "context action must be assign_and_sell_covered_call"
            )
        if context.threatened_side is not ThreatenedSide.PUT:
            raise ValueError("assignment is only valid for threatened put side")
        if contracts <= 0:
            raise ValueError("contracts must be greater than zero")
        for name, value in (
            ("put_premium_per_share", put_premium_per_share),
            ("roll_credit_per_share", roll_credit_per_share),
        ):
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and must not be negative")
        if not daily_bars:
            raise ValueError("daily_bars must not be empty")
        if any(bar.date < context.decision_date for bar in daily_bars):
            raise ValueError("daily_bars must not contain dates before decision_date")
        if any(
            current.date >= following.date
            for current, following in zip(daily_bars, daily_bars[1:])
        ):
            raise ValueError("daily_bars must be ordered by ascending unique date")
        if any(
            not math.isfinite(value) or value <= 0
            for bar in daily_bars
            for value in (bar.open, bar.high, bar.low, bar.close)
        ):
            raise ValueError("daily bar prices must be finite and greater than zero")

        previous_expiration: date | None = None
        for sale in covered_call_sales:
            if sale.sale_date < context.decision_date:
                raise ValueError(
                    "covered-call sale must not be before assignment date"
                )
            if previous_expiration is not None and sale.sale_date <= previous_expiration:
                raise ValueError("covered-call sales must not overlap")
            previous_expiration = sale.expiration_date
