from dataclasses import dataclass

from app.analysis.expected_move import ExpectedMove
from app.analysis.historical_earnings_price_analyzer import (
    HistoricalEarningsPriceAnalysis,
)
from app.analysis.historical_strike_adjusted_selector import (
    HistoricalStrikeAdjustedSelection,
    HistoricalStrikeAdjustedSelector,
)
from app.analysis.historical_strike_selection_service import (
    HistoricalStrikeSelectionResult,
    HistoricalStrikeSelectionService,
)
from app.analysis.historical_strike_selector import (
    HistoricalStrikeSelectionPolicy,
)
from app.analysis.strategy import Strategy
from app.marketdata.models import ExpirationChain


@dataclass(frozen=True, slots=True)
class HistoricalStrategySelectionResult:
    historical_result: HistoricalStrikeSelectionResult
    adjusted_selection: HistoricalStrikeAdjustedSelection


class HistoricalStrategySelectorAdapter:

    def __init__(
        self,
        historical_selection_service: (
            HistoricalStrikeSelectionService
        ),
        adjusted_selector: HistoricalStrikeAdjustedSelector,
    ) -> None:
        self.historical_selection_service = (
            historical_selection_service
        )
        self.adjusted_selector = adjusted_selector

    def select(
        self,
        chain: ExpirationChain,
        underlying_price: float,
        expected_move: ExpectedMove,
        price_analyses: tuple[
            HistoricalEarningsPriceAnalysis,
            ...,
        ],
        exit_trading_day_index: int,
        call_thresholds: tuple[float, ...],
        put_thresholds: tuple[float, ...],
        policy: HistoricalStrikeSelectionPolicy,
        strategy: Strategy = Strategy.IRON_CONDOR,
    ) -> HistoricalStrategySelectionResult:
        if underlying_price <= 0:
            raise ValueError(
                "underlying_price must be greater than zero"
            )

        if expected_move.percent <= 0:
            raise ValueError(
                "expected_move.percent must be greater than zero"
            )

        expected_move_percent = expected_move.percent * 100

        historical_result = (
            self.historical_selection_service.select(
                price_analyses=price_analyses,
                expected_move_percent=expected_move_percent,
                exit_trading_day_index=(
                    exit_trading_day_index
                ),
                call_thresholds=call_thresholds,
                put_thresholds=put_thresholds,
                policy=policy,
            )
        )

        adjusted_selection = self.adjusted_selector.select(
            chain=chain,
            underlying_price=underlying_price,
            historical_selection=(
                historical_result.selection
            ),
            strategy=strategy,
        )

        return HistoricalStrategySelectionResult(
            historical_result=historical_result,
            adjusted_selection=adjusted_selection,
        )