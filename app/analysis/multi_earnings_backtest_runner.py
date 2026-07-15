from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.analysis.backtest_outcome_analyzer import (
    BacktestOutcome,
    BacktestOutcomeAnalyzer,
)
from app.analysis.strategy_selector import StrikeSelectionSource
from app.analysis.strike_selection import StrikeSelection
from app.marketdata.price_history_provider import DailyBar


@dataclass(frozen=True, slots=True)
class EarningsBacktestCase:
    report_date: date
    selection: StrikeSelection
    daily_bars: tuple[DailyBar, ...]
    reference_price: float
    exit_trading_day_index: int
    selection_source: StrikeSelectionSource


@dataclass(frozen=True, slots=True)
class EarningsBacktestResult:
    report_date: date
    selection_source: StrikeSelectionSource
    outcome: BacktestOutcome


@dataclass(frozen=True, slots=True)
class BacktestMetrics:
    observation_count: int
    inside_rate: float
    put_touch_rate: float
    call_touch_rate: float
    put_finish_outside_rate: float
    call_finish_outside_rate: float
    average_max_adverse_move_percent: float
    average_max_favorable_move_percent: float
    average_holding_days: float


@dataclass(frozen=True, slots=True)
class SourceBacktestMetrics:
    selection_source: StrikeSelectionSource
    metrics: BacktestMetrics


@dataclass(frozen=True, slots=True)
class MultiEarningsBacktestSummary:
    symbol: str
    results: tuple[EarningsBacktestResult, ...]
    overall: BacktestMetrics
    by_selection_source: tuple[SourceBacktestMetrics, ...]


class MultiEarningsBacktestRunner:
    """Evaluate and aggregate multiple historical earnings decisions.

    Each case must already contain a decision made without future data. This
    runner only evaluates that frozen decision against the later underlying
    bars and aggregates the resulting risk metrics. It does not estimate
    option P&L.
    """

    def __init__(
        self,
        outcome_analyzer: BacktestOutcomeAnalyzer | None = None,
    ) -> None:
        self.outcome_analyzer = outcome_analyzer or BacktestOutcomeAnalyzer()

    def run(
        self,
        symbol: str,
        cases: tuple[EarningsBacktestCase, ...],
    ) -> MultiEarningsBacktestSummary:
        normalized_symbol = symbol.strip().upper()
        if not normalized_symbol:
            raise ValueError("symbol must not be empty")
        if not cases:
            raise ValueError("cases must not be empty")

        ordered_cases = tuple(sorted(cases, key=lambda item: item.report_date))
        if len({case.report_date for case in ordered_cases}) != len(ordered_cases):
            raise ValueError("cases must have unique report dates")

        results = tuple(
            EarningsBacktestResult(
                report_date=case.report_date,
                selection_source=case.selection_source,
                outcome=self.outcome_analyzer.analyze(
                    selection=case.selection,
                    daily_bars=case.daily_bars,
                    reference_price=case.reference_price,
                    exit_trading_day_index=case.exit_trading_day_index,
                ),
            )
            for case in ordered_cases
        )

        source_metrics = tuple(
            SourceBacktestMetrics(
                selection_source=source,
                metrics=self._metrics(
                    tuple(
                        result
                        for result in results
                        if result.selection_source is source
                    )
                ),
            )
            for source in StrikeSelectionSource
            if any(result.selection_source is source for result in results)
        )

        return MultiEarningsBacktestSummary(
            symbol=normalized_symbol,
            results=results,
            overall=self._metrics(results),
            by_selection_source=source_metrics,
        )

    @staticmethod
    def _metrics(
        results: tuple[EarningsBacktestResult, ...],
    ) -> BacktestMetrics:
        count = len(results)
        if count == 0:
            raise ValueError("results must not be empty")

        outcomes = tuple(result.outcome for result in results)

        return BacktestMetrics(
            observation_count=count,
            inside_rate=sum(
                outcome.finished_inside_short_strikes for outcome in outcomes
            ) / count,
            put_touch_rate=sum(outcome.put_touched for outcome in outcomes) / count,
            call_touch_rate=sum(outcome.call_touched for outcome in outcomes) / count,
            put_finish_outside_rate=sum(
                outcome.put_finished_outside for outcome in outcomes
            ) / count,
            call_finish_outside_rate=sum(
                outcome.call_finished_outside for outcome in outcomes
            ) / count,
            average_max_adverse_move_percent=sum(
                outcome.max_adverse_move_percent for outcome in outcomes
            ) / count,
            average_max_favorable_move_percent=sum(
                outcome.max_favorable_move_percent for outcome in outcomes
            ) / count,
            average_holding_days=sum(
                outcome.holding_days for outcome in outcomes
            ) / count,
        )
