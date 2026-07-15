from collections.abc import Callable
from datetime import date, timedelta

from app.analysis.historical_earnings_analysis_analyzer import (
    HistoricalEarningsAnalysisAnalyzer,
)
from app.analysis.historical_earnings_analysis_loader import (
    HistoricalEarningsAnalysisLoader,
)
from app.analysis.historical_strike_selector import (
    HistoricalStrikeSelectionPolicy,
)
from app.analysis.historical_strategy_selection_inputs import (
    HistoricalStrategySelectionInputs,
)
from app.analysis.reference_price_resolver import ReferencePriceResolver
from app.marketdata.earnings_api_provider import HistoricalEarningsReaction


class HistoricalStrategySelectionInputsLoader:

    def __init__(
        self,
        analysis_loader: HistoricalEarningsAnalysisLoader,
        analysis_analyzer: HistoricalEarningsAnalysisAnalyzer,
        reference_price_resolver: ReferencePriceResolver,
        exit_trading_day_index: int,
        call_thresholds: tuple[float, ...],
        put_thresholds: tuple[float, ...],
        policy: HistoricalStrikeSelectionPolicy,
        end_date_resolver: Callable[
            [HistoricalEarningsReaction],
            date,
        ] | None = None,
    ) -> None:
        if exit_trading_day_index < 0:
            raise ValueError(
                "exit_trading_day_index must not be negative"
            )

        self.analysis_loader = analysis_loader
        self.analysis_analyzer = analysis_analyzer
        self.reference_price_resolver = reference_price_resolver
        self.exit_trading_day_index = exit_trading_day_index
        self.call_thresholds = call_thresholds
        self.put_thresholds = put_thresholds
        self.policy = policy
        self.end_date_resolver = (
            end_date_resolver
            if end_date_resolver is not None
            else self._earnings_week_friday
        )

    def load(
        self,
        symbol: str,
    ) -> HistoricalStrategySelectionInputs | None:
        analysis = self.analysis_loader.load(
            symbol=symbol,
            end_date_resolver=self.end_date_resolver,
        )

        if not analysis.price_series:
            return None

        result = self.analysis_analyzer.analyze(
            analysis=analysis,
            reference_price_resolver=(
                self.reference_price_resolver
            ),
        )

        minimum_required_days = max(
            1,
            self.exit_trading_day_index,
        )
        usable_price_analyses = tuple(
            price_analysis
            for price_analysis in result.price_analyses
            if len(price_analysis.daily_moves)
            >= minimum_required_days
        )

        if not usable_price_analyses:
            return None

        return HistoricalStrategySelectionInputs(
            price_analyses=usable_price_analyses,
            exit_trading_day_index=self.exit_trading_day_index,
            call_thresholds=self.call_thresholds,
            put_thresholds=self.put_thresholds,
            policy=self.policy,
        )

    @staticmethod
    def _earnings_week_friday(
        earnings: HistoricalEarningsReaction,
    ) -> date:
        days_until_friday = (4 - earnings.report_date.weekday()) % 7
        return earnings.report_date + timedelta(
            days=days_until_friday
        )
