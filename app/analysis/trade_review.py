from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.analysis.backtest_outcome_analyzer import (
    BacktestOutcome,
    BacktestOutcomeAnalyzer,
)
from app.analysis.strike_selection import StrikeSelection
from app.marketdata.price_history_provider import DailyBar


@dataclass(frozen=True, slots=True)
class ExitReview:
    trading_day_index: int
    exit_date: date
    exit_close: float
    finished_inside_short_strikes: bool
    put_touched: bool
    call_touched: bool
    put_finished_outside: bool
    call_finished_outside: bool


@dataclass(frozen=True, slots=True)
class TradeReview:
    selected_exit: ExitReview
    alternative_exits: tuple[ExitReview, ...]
    assessment: str
    observations: tuple[str, ...]
    max_adverse_move_percent: float
    max_favorable_move_percent: float


class TradeReviewAnalyzer:
    """Compare a selected earnings exit with every available alternative.

    The review intentionally evaluates the underlying path only. It does not
    infer option P&L because historical option prices are not part of the
    current data model.
    """

    def __init__(
        self,
        outcome_analyzer: BacktestOutcomeAnalyzer | None = None,
    ) -> None:
        self.outcome_analyzer = outcome_analyzer or BacktestOutcomeAnalyzer()

    def analyze(
        self,
        selection: StrikeSelection,
        daily_bars: tuple[DailyBar, ...],
        reference_price: float,
        selected_exit_trading_day_index: int,
    ) -> TradeReview:
        if not daily_bars:
            raise ValueError("daily_bars must not be empty")
        if selected_exit_trading_day_index <= 0:
            raise ValueError(
                "selected_exit_trading_day_index must be greater than zero"
            )
        if selected_exit_trading_day_index > len(daily_bars):
            raise ValueError(
                "daily_bars do not contain the selected exit trading day"
            )

        outcomes = tuple(
            self.outcome_analyzer.analyze(
                selection=selection,
                daily_bars=daily_bars,
                reference_price=reference_price,
                exit_trading_day_index=day_index,
            )
            for day_index in range(1, len(daily_bars) + 1)
        )
        selected = outcomes[selected_exit_trading_day_index - 1]
        alternatives = tuple(
            outcome
            for outcome in outcomes
            if outcome.exit_trading_day_index
            != selected_exit_trading_day_index
        )

        return TradeReview(
            selected_exit=self._to_exit_review(selected),
            alternative_exits=tuple(
                self._to_exit_review(outcome)
                for outcome in alternatives
            ),
            assessment=self._assessment(selected),
            observations=self._observations(
                selected=selected,
                outcomes=outcomes,
            ),
            max_adverse_move_percent=selected.max_adverse_move_percent,
            max_favorable_move_percent=selected.max_favorable_move_percent,
        )

    @staticmethod
    def _to_exit_review(outcome: BacktestOutcome) -> ExitReview:
        return ExitReview(
            trading_day_index=outcome.exit_trading_day_index,
            exit_date=outcome.exit_date,
            exit_close=outcome.exit_close,
            finished_inside_short_strikes=(
                outcome.finished_inside_short_strikes
            ),
            put_touched=outcome.put_touched,
            call_touched=outcome.call_touched,
            put_finished_outside=outcome.put_finished_outside,
            call_finished_outside=outcome.call_finished_outside,
        )

    @staticmethod
    def _assessment(outcome: BacktestOutcome) -> str:
        if not outcome.finished_inside_short_strikes:
            return "Strike am gewählten Exit verletzt"
        if outcome.put_touched or outcome.call_touched:
            return "Erfolgreich, aber mit zwischenzeitlichem Touch-Risiko"
        return "Sehr gut: innerhalb der Short-Strikes ohne Berührung"

    @staticmethod
    def _observations(
        selected: BacktestOutcome,
        outcomes: tuple[BacktestOutcome, ...],
    ) -> tuple[str, ...]:
        observations: list[str] = []

        earlier = tuple(
            outcome
            for outcome in outcomes
            if outcome.exit_trading_day_index
            < selected.exit_trading_day_index
        )
        if any(
            outcome.finished_inside_short_strikes
            and not outcome.put_touched
            and not outcome.call_touched
            for outcome in earlier
        ):
            observations.append(
                "Ein früherer Exit wäre ebenfalls innerhalb der Strikes "
                "und ohne Touch möglich gewesen."
            )

        later = tuple(
            outcome
            for outcome in outcomes
            if outcome.exit_trading_day_index
            > selected.exit_trading_day_index
        )
        if any(
            not outcome.finished_inside_short_strikes
            for outcome in later
        ):
            observations.append(
                "Ein späterer Exit hätte zu einem Schlusskurs außerhalb "
                "der Short-Strikes geführt."
            )
        elif any(
            outcome.put_touched or outcome.call_touched
            for outcome in later
        ):
            observations.append(
                "Ein späterer Exit hätte zusätzliches Touch-Risiko erzeugt."
            )

        if selected.put_touched and selected.call_touched:
            observations.append(
                "Bis zum gewählten Exit wurden beide Short-Strikes berührt."
            )
        elif selected.put_touched:
            observations.append(
                "Bis zum gewählten Exit wurde der Short Put berührt."
            )
        elif selected.call_touched:
            observations.append(
                "Bis zum gewählten Exit wurde der Short Call berührt."
            )

        if not observations:
            observations.append(
                "Der gewählte Exit kontrollierte das beobachtete "
                "Underlying-Risiko ohne erkennbare Alternative besser."
            )

        return tuple(observations)
