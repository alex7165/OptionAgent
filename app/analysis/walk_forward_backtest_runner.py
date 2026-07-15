from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from app.analysis.expected_move import ExpectedMove
from app.analysis.historical_earnings_price_analyzer import (
    HistoricalEarningsPriceAnalysis,
)
from app.analysis.historical_strike_selector import (
    HistoricalStrikeSelectionPolicy,
)
from app.analysis.multi_earnings_backtest_runner import (
    EarningsBacktestCase,
    MultiEarningsBacktestRunner,
    MultiEarningsBacktestSummary,
)
from app.analysis.strategy import Strategy
from app.analysis.strategy_selector import (
    StrategyStrikeSelectionResult,
    StrikeSelectionSource,
)
from app.marketdata.models import ExpirationChain
from app.marketdata.price_history_provider import DailyBar


class WalkForwardDecisionSelector(Protocol):
    def select_strikes_with_details(
        self,
        *,
        chain: ExpirationChain,
        underlying_price: float,
        expected_move: ExpectedMove,
        strategy: Strategy = Strategy.IRON_CONDOR,
        price_analyses: tuple[
            HistoricalEarningsPriceAnalysis,
            ...,
        ] | None = None,
        exit_trading_day_index: int | None = None,
        call_thresholds: tuple[float, ...] | None = None,
        put_thresholds: tuple[float, ...] | None = None,
        policy: HistoricalStrikeSelectionPolicy | None = None,
    ) -> StrategyStrikeSelectionResult:
        ...


@dataclass(frozen=True, slots=True)
class WalkForwardBacktestCase:
    report_date: date
    chain: ExpirationChain
    expected_move: ExpectedMove
    reference_price: float
    daily_bars: tuple[DailyBar, ...]
    strategy: Strategy = Strategy.IRON_CONDOR
    fallback_exit_trading_day_index: int | None = None


@dataclass(frozen=True, slots=True)
class WalkForwardDecision:
    report_date: date
    training_observation_count: int
    selection_source: StrikeSelectionSource
    exit_trading_day_index: int
    selection_result: StrategyStrikeSelectionResult


@dataclass(frozen=True, slots=True)
class WalkForwardBacktestSummary:
    symbol: str
    decisions: tuple[WalkForwardDecision, ...]
    backtest: MultiEarningsBacktestSummary


class WalkForwardBacktestRunner:
    """Create and evaluate chronological earnings decisions without leakage.

    For every case, only historical earnings analyses whose report date is
    strictly earlier than the case report date are passed to the historical
    selector. If the available training sample is below the configured
    minimum, the expected-move selector is used instead.
    """

    def __init__(
        self,
        historical_selector: WalkForwardDecisionSelector,
        fallback_selector: WalkForwardDecisionSelector,
        multi_runner: MultiEarningsBacktestRunner | None = None,
        minimum_training_observations: int = 1,
    ) -> None:
        if minimum_training_observations < 1:
            raise ValueError(
                "minimum_training_observations must be greater than zero"
            )

        self.historical_selector = historical_selector
        self.fallback_selector = fallback_selector
        self.multi_runner = multi_runner or MultiEarningsBacktestRunner()
        self.minimum_training_observations = minimum_training_observations

    def run(
        self,
        symbol: str,
        cases: tuple[WalkForwardBacktestCase, ...],
        historical_price_analyses: tuple[
            HistoricalEarningsPriceAnalysis,
            ...,
        ],
        call_thresholds: tuple[float, ...],
        put_thresholds: tuple[float, ...],
        policy: HistoricalStrikeSelectionPolicy,
    ) -> WalkForwardBacktestSummary:
        normalized_symbol = symbol.strip().upper()
        if not normalized_symbol:
            raise ValueError("symbol must not be empty")
        if not cases:
            raise ValueError("cases must not be empty")

        ordered_cases = tuple(sorted(cases, key=lambda item: item.report_date))
        if len({case.report_date for case in ordered_cases}) != len(ordered_cases):
            raise ValueError("cases must have unique report dates")

        decisions: list[WalkForwardDecision] = []
        evaluated_cases: list[EarningsBacktestCase] = []

        for case in ordered_cases:
            self._validate_case(case)
            training_analyses = tuple(
                analysis
                for analysis in historical_price_analyses
                if analysis.earnings.report_date < case.report_date
            )

            if len(training_analyses) >= self.minimum_training_observations:
                selection_result = self.historical_selector.select_strikes_with_details(
                    chain=case.chain,
                    underlying_price=case.reference_price,
                    expected_move=case.expected_move,
                    strategy=case.strategy,
                    price_analyses=training_analyses,
                    exit_trading_day_index=0,
                    call_thresholds=call_thresholds,
                    put_thresholds=put_thresholds,
                    policy=policy,
                )
                exit_day = self._historical_exit_day(selection_result)
            else:
                selection_result = self.fallback_selector.select_strikes_with_details(
                    chain=case.chain,
                    underlying_price=case.reference_price,
                    expected_move=case.expected_move,
                    strategy=case.strategy,
                )
                exit_day = (
                    case.fallback_exit_trading_day_index
                    if case.fallback_exit_trading_day_index is not None
                    else len(case.daily_bars)
                )

            decisions.append(
                WalkForwardDecision(
                    report_date=case.report_date,
                    training_observation_count=len(training_analyses),
                    selection_source=selection_result.source,
                    exit_trading_day_index=exit_day,
                    selection_result=selection_result,
                )
            )
            evaluated_cases.append(
                EarningsBacktestCase(
                    report_date=case.report_date,
                    selection=selection_result.strike_selection,
                    daily_bars=case.daily_bars,
                    reference_price=case.reference_price,
                    exit_trading_day_index=exit_day,
                    selection_source=selection_result.source,
                )
            )

        backtest = self.multi_runner.run(
            symbol=normalized_symbol,
            cases=tuple(evaluated_cases),
        )
        return WalkForwardBacktestSummary(
            symbol=normalized_symbol,
            decisions=tuple(decisions),
            backtest=backtest,
        )

    @staticmethod
    def _historical_exit_day(
        result: StrategyStrikeSelectionResult,
    ) -> int:
        historical_result = result.historical_result
        if historical_result is None:
            raise ValueError(
                "historical selection result must include historical details"
            )

        call = historical_result.selection.call_recommendation
        put = historical_result.selection.put_recommendation
        if call is None or put is None:
            raise ValueError(
                "historical selection must include both recommendations"
            )
        if call.exit_trading_day_index != put.exit_trading_day_index:
            raise ValueError(
                "historical recommendations must use the same exit day"
            )
        return call.exit_trading_day_index

    @staticmethod
    def _validate_case(case: WalkForwardBacktestCase) -> None:
        if case.reference_price <= 0:
            raise ValueError("reference_price must be greater than zero")
        if not case.daily_bars:
            raise ValueError("daily_bars must not be empty")
        if (
            case.fallback_exit_trading_day_index is not None
            and case.fallback_exit_trading_day_index <= 0
        ):
            raise ValueError(
                "fallback_exit_trading_day_index must be greater than zero"
            )
