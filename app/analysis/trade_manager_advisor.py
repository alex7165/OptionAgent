from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite
from enum import StrEnum

from app.analysis.entry_decision_snapshot import EntryDecisionSnapshot
from app.marketdata.models import OptionQuote
from app.analysis.trade_management_chart_context import TradeManagementChartContext


class ManagementAction(StrEnum):
    CLOSE = "Schließen"
    HOLD = "Halten"
    ROLL_CALL = "Call nach oben rollen"
    ADJUST_DELTA_HEDGE = "Delta-Hedge anpassen"


@dataclass(frozen=True, slots=True)
class ComparableManagementCase:
    report_date: date
    maximum_move_percent: float
    maximum_move_trading_day: int
    friday_close_move_percent: float
    made_all_time_high: bool


@dataclass(frozen=True, slots=True)
class HistoricalManagementContext:
    observation_count: int
    probability_finish_back_inside: float | None
    probability_continue_higher: float | None
    average_remaining_move_percent: float | None
    total_observation_count: int | None = None
    comparable_cases: tuple[ComparableManagementCase, ...] = ()


@dataclass(frozen=True, slots=True)
class TradeManagerMarketState:
    underlying_price: float
    days_to_expiration: int
    short_put: OptionQuote
    short_call: OptionQuote
    replacement_call: OptionQuote | None = None
    short_call_delta: float | None = None
    short_put_delta: float | None = None
    existing_hedge_shares: int = 0
    chart_context: TradeManagementChartContext | None = None


@dataclass(frozen=True, slots=True)
class ManagementAlternative:
    action: ManagementAction
    available: bool
    score: float
    estimated_cash_flow: float | None
    details: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TradeManagementAdvice:
    symbol: str
    strategy: str
    breached_side: str | None
    breach_percent: float
    recommended_action: ManagementAction
    alternatives: tuple[ManagementAlternative, ...]
    history_observation_count: int


class TradeManagerAdvisor:
    """Compare management choices for an existing short strangle.

    Cash flows use executable-side estimates: buying shorts at ask and selling
    a replacement call at bid. They are estimates, not guaranteed fills.
    """

    def advise(
        self,
        entry: EntryDecisionSnapshot,
        market: TradeManagerMarketState,
        history: HistoricalManagementContext,
    ) -> TradeManagementAdvice:
        if market.underlying_price <= 0:
            raise ValueError("underlying_price must be greater than zero")
        if market.days_to_expiration < 0:
            raise ValueError("days_to_expiration must not be negative")

        call_breach = max(
            0.0,
            (market.underlying_price / entry.short_call_strike - 1) * 100,
        )
        put_breach = max(
            0.0,
            (entry.short_put_strike / market.underlying_price - 1) * 100,
        )
        breached_side = None
        breach_percent = 0.0
        if call_breach > 0 or put_breach > 0:
            breached_side = "call" if call_breach >= put_breach else "put"
            breach_percent = max(call_breach, put_breach)

        close_cost = self._sum_asks(market.short_put, market.short_call)
        close_score = 45.0 + min(35.0, breach_percent * 6.0)
        if market.days_to_expiration <= 2:
            close_score += 10.0
        if (history.probability_continue_higher or 0) >= 0.60:
            close_score += 10.0
        if market.chart_context is not None:
            close_score += min(15.0, market.chart_context.revaluation_signal_count * 3.0)

        hold_score = 55.0 - min(45.0, breach_percent * 8.0)
        if history.probability_finish_back_inside is not None:
            hold_score += 30.0 * history.probability_finish_back_inside
        if market.days_to_expiration <= 2 and breach_percent > 0:
            hold_score -= 15.0
        if market.chart_context is not None:
            hold_score -= min(18.0, market.chart_context.revaluation_signal_count * 3.0)

        roll = self._roll_alternative(entry, market, history, breach_percent)
        hedge = self._hedge_alternative(market, history, breached_side)

        alternatives = (
            ManagementAlternative(
                action=ManagementAction.CLOSE,
                available=close_cost is not None,
                score=self._bounded(close_score),
                estimated_cash_flow=(-close_cost if close_cost is not None else None),
                details=(
                    "Beendet Gamma- und Gap-Risiko sofort.",
                    "Rückkaufkosten aus aktuellen Ask-Preisen geschätzt.",
                ),
            ),
            ManagementAlternative(
                action=ManagementAction.HOLD,
                available=True,
                score=self._bounded(hold_score),
                estimated_cash_flow=0.0,
                details=(
                    "Kein zusätzlicher Trade.",
                    "Bei kurzem Restlauf und verletztem Strike bleibt hohes Gamma-Risiko.",
                ),
            ),
            roll,
            hedge,
        )
        available = tuple(item for item in alternatives if item.available)
        recommended = max(available, key=lambda item: item.score).action
        return TradeManagementAdvice(
            symbol=entry.symbol,
            strategy=entry.strategy.value,
            breached_side=breached_side,
            breach_percent=breach_percent,
            recommended_action=recommended,
            alternatives=alternatives,
            history_observation_count=history.observation_count,
        )

    def _roll_alternative(
        self,
        entry: EntryDecisionSnapshot,
        market: TradeManagerMarketState,
        history: HistoricalManagementContext,
        breach_percent: float,
    ) -> ManagementAlternative:
        replacement = market.replacement_call
        available = (
            replacement is not None
            and replacement.strike > entry.short_call_strike
            and replacement.strike > market.underlying_price
            and market.short_call.ask is not None
            and replacement.bid is not None
        )
        cash_flow = None
        details: list[str] = []
        score = 30.0
        if available and replacement is not None:
            cash_flow = replacement.bid - market.short_call.ask
            new_buffer = (replacement.strike / market.underlying_price - 1) * 100
            score = 62.0 + min(18.0, max(0.0, new_buffer) * 4.0)
            score -= min(20.0, breach_percent * 2.0)
            if cash_flow >= 0:
                score += 8.0
            if (history.probability_continue_higher or 0) >= 0.60:
                score += 5.0
            if market.chart_context is not None:
                score += min(10.0, market.chart_context.revaluation_signal_count * 2.0)
            details.extend(
                (
                    f"Neuer Call {replacement.strike:g}; Abstand zum aktuellen Kurs {new_buffer:.2f} %.",
                    f"Geschätzter Roll-Cashflow {cash_flow:.2f} USD je Aktie (Bid/Ask).",
                )
            )
        else:
            details.append("Kein geeigneter liquider Call oberhalb des aktuellen Kurses verfügbar.")
        return ManagementAlternative(
            action=ManagementAction.ROLL_CALL,
            available=available,
            score=self._bounded(score),
            estimated_cash_flow=cash_flow,
            details=tuple(details),
        )

    def _hedge_alternative(
        self,
        market: TradeManagerMarketState,
        history: HistoricalManagementContext,
        breached_side: str | None,
    ) -> ManagementAlternative:
        call_delta = self._finite_delta(
            market.short_call_delta, market.short_call.delta
        )
        put_delta = self._finite_delta(
            market.short_put_delta, market.short_put.delta
        )
        available = breached_side == "call" and call_delta is not None
        target_shares = None
        adjustment = None
        score = 40.0
        details: list[str] = []
        if available and call_delta is not None:
            # Long-option deltas: call positive, put negative. Shorting both
            # reverses their sign. Long shares offset the resulting net delta.
            effective_put_delta = put_delta if put_delta is not None else 0.0
            net_option_delta_shares = -(call_delta + effective_put_delta) * 100
            target_shares = max(0, round(-net_option_delta_shares))
            adjustment = target_shares - market.existing_hedge_shares
            score = 58.0
            if (history.probability_continue_higher or 0) >= 0.60:
                score += 12.0
            direction = "kaufen" if adjustment > 0 else "verkaufen"
            if adjustment == 0:
                action_text = "Aktuell keine weitere Aktienanpassung nötig."
            else:
                action_text = f"Heute {abs(adjustment)} GS-Aktien {direction}."
            details.extend(
                (
                    f"Netto-Optionsdelta ungefähr {net_option_delta_shares:+.0f} Aktienäquivalente.",
                    f"Zielbestand Hedge: {target_shares} Aktien; aktuell: {market.existing_hedge_shares}.",
                    action_text,
                    "Hedge bei jeder Neubewertung neu berechnen und spätestens beim Schließen der Optionen vollständig auflösen.",
                    "Ein partieller Hedge darf nicht unbeaufsichtigt bis zur Ausübung stehen bleiben.",
                )
            )
        else:
            details.append(
                "Optionsdelta fehlt; zuerst OptionStrat-Delta verwenden, sonst Delta aus IV, Laufzeit und Optionspreis berechnen."
            )
        return ManagementAlternative(
            action=ManagementAction.ADJUST_DELTA_HEDGE,
            available=available,
            score=self._bounded(score),
            estimated_cash_flow=(
                -adjustment * market.underlying_price
                if adjustment is not None
                else None
            ),
            details=tuple(details),
        )

    @staticmethod
    def _finite_delta(*values: float | None) -> float | None:
        for value in values:
            if value is None:
                continue
            number = float(value)
            if isfinite(number):
                return number
        return None

    @staticmethod
    def _sum_asks(*quotes: OptionQuote) -> float | None:
        if any(quote.ask is None for quote in quotes):
            return None
        return sum(float(quote.ask) for quote in quotes)

    @staticmethod
    def _bounded(value: float) -> float:
        return max(0.0, min(100.0, value))
