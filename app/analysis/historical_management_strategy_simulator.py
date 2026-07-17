from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from app.analysis.strike_selection import StrikeSelection
from app.marketdata.price_history_provider import DailyBar


class HistoricalManagementStrategy(StrEnum):
    CLOSE_AFTER_REACTION = "close_after_reaction"
    HOLD_TO_FRIDAY = "hold_to_friday"


@dataclass(frozen=True, slots=True)
class HistoricalManagementStrategyOutcome:
    strategy: HistoricalManagementStrategy
    decision_date: date
    decision_trading_day_index: int
    decision_close: float
    decision_move_percent: float
    evaluation_end_date: date
    evaluation_end_close: float
    evaluation_end_move_percent: float
    finished_inside_short_strikes: bool
    maximum_move_after_decision_percent: float
    minimum_move_after_decision_percent: float
    observations: tuple[str, ...]


class HistoricalManagementStrategySimulator:
    """Create underlying-based labels for historical management strategies.

    Historical option prices are not available in the current data model.
    Therefore, this simulator does not invent option P&L. It records the
    observable underlying path that followed each management decision so the
    learning layer can later combine these labels with real option data.
    """

    def simulate_baselines(
        self,
        selection: StrikeSelection,
        daily_bars: tuple[DailyBar, ...],
        reference_price: float,
        reaction_trading_day_index: int = 1,
    ) -> tuple[HistoricalManagementStrategyOutcome, ...]:
        self._validate(
            selection=selection,
            daily_bars=daily_bars,
            reference_price=reference_price,
            reaction_trading_day_index=reaction_trading_day_index,
        )

        reaction_bar = daily_bars[reaction_trading_day_index - 1]
        friday_bar = daily_bars[-1]

        return (
            self._build_outcome(
                strategy=HistoricalManagementStrategy.CLOSE_AFTER_REACTION,
                decision_bar=reaction_bar,
                decision_trading_day_index=reaction_trading_day_index,
                evaluation_bars=daily_bars[reaction_trading_day_index - 1 :],
                evaluation_end_bar=reaction_bar,
                selection=selection,
                reference_price=reference_price,
                observations=(
                    "Position wird zum Schluss des ersten Reaktionstags geschlossen.",
                    "Kein historisches Options-P&L berechnet; gespeichert wird nur der spätere Underlying-Pfad.",
                ),
            ),
            self._build_outcome(
                strategy=HistoricalManagementStrategy.HOLD_TO_FRIDAY,
                decision_bar=reaction_bar,
                decision_trading_day_index=reaction_trading_day_index,
                evaluation_bars=daily_bars[reaction_trading_day_index - 1 :],
                evaluation_end_bar=friday_bar,
                selection=selection,
                reference_price=reference_price,
                observations=(
                    "Position bleibt nach dem ersten Reaktionstag bis zum letzten verfügbaren Handelstag der Earnings-Woche offen.",
                    "Kein historisches Options-P&L berechnet; Ergebnis basiert auf dem Underlying-Schlusskurs.",
                ),
            ),
        )

    @staticmethod
    def _build_outcome(
        *,
        strategy: HistoricalManagementStrategy,
        decision_bar: DailyBar,
        decision_trading_day_index: int,
        evaluation_bars: tuple[DailyBar, ...],
        evaluation_end_bar: DailyBar,
        selection: StrikeSelection,
        reference_price: float,
        observations: tuple[str, ...],
    ) -> HistoricalManagementStrategyOutcome:
        maximum_high = max(bar.high for bar in evaluation_bars)
        minimum_low = min(bar.low for bar in evaluation_bars)
        end_close = evaluation_end_bar.close

        return HistoricalManagementStrategyOutcome(
            strategy=strategy,
            decision_date=decision_bar.date,
            decision_trading_day_index=decision_trading_day_index,
            decision_close=decision_bar.close,
            decision_move_percent=(decision_bar.close / reference_price - 1) * 100,
            evaluation_end_date=evaluation_end_bar.date,
            evaluation_end_close=end_close,
            evaluation_end_move_percent=(end_close / reference_price - 1) * 100,
            finished_inside_short_strikes=(
                selection.put.strike <= end_close <= selection.call.strike
            ),
            maximum_move_after_decision_percent=(
                maximum_high / reference_price - 1
            ) * 100,
            minimum_move_after_decision_percent=(
                minimum_low / reference_price - 1
            ) * 100,
            observations=observations,
        )

    @staticmethod
    def _validate(
        *,
        selection: StrikeSelection,
        daily_bars: tuple[DailyBar, ...],
        reference_price: float,
        reaction_trading_day_index: int,
    ) -> None:
        if selection.put is None or selection.call is None:
            raise ValueError("selection must contain short put and short call")
        if reference_price <= 0:
            raise ValueError("reference_price must be greater than zero")
        if not daily_bars:
            raise ValueError("daily_bars must not be empty")
        if reaction_trading_day_index <= 0:
            raise ValueError(
                "reaction_trading_day_index must be greater than zero"
            )
        if reaction_trading_day_index > len(daily_bars):
            raise ValueError(
                "daily_bars do not contain the requested reaction trading day"
            )
        if any(
            current.date >= following.date
            for current, following in zip(daily_bars, daily_bars[1:])
        ):
            raise ValueError(
                "daily_bars must be ordered by ascending unique date"
            )
