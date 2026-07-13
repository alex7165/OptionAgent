from dataclasses import dataclass

from app.analysis.historical_earnings_price_analyzer import (
    HistoricalEarningsPriceAnalysis,
)
from app.analysis.historical_outcome_analyzer import (
    HistoricalOutcome,
    HistoricalOutcomeAnalyzer,
)
from app.analysis.historical_strike_risk_grid_analyzer import (
    HistoricalStrikeRiskGrid,
    HistoricalStrikeRiskGridAnalyzer,
)
from app.analysis.historical_strike_selector import (
    HistoricalStrikeSelection,
    HistoricalStrikeSelectionPolicy,
    HistoricalStrikeSelector,
)


@dataclass(frozen=True, slots=True)
class HistoricalStrikeSelectionResult:
    outcomes: tuple[HistoricalOutcome, ...]
    risk_grid: HistoricalStrikeRiskGrid
    selection: HistoricalStrikeSelection


class HistoricalStrikeSelectionService:

    def __init__(
        self,
        outcome_analyzer: HistoricalOutcomeAnalyzer,
        risk_grid_analyzer: HistoricalStrikeRiskGridAnalyzer,
        strike_selector: HistoricalStrikeSelector,
    ) -> None:
        self.outcome_analyzer = outcome_analyzer
        self.risk_grid_analyzer = risk_grid_analyzer
        self.strike_selector = strike_selector

    def select(
        self,
        price_analyses: tuple[
            HistoricalEarningsPriceAnalysis,
            ...,
        ],
        expected_move_percent: float,
        exit_trading_day_index: int,
        call_thresholds: tuple[float, ...],
        put_thresholds: tuple[float, ...],
        policy: HistoricalStrikeSelectionPolicy,
    ) -> HistoricalStrikeSelectionResult:
        if not price_analyses:
            raise ValueError(
                "price_analyses must not be empty"
            )

        outcomes = tuple(
            self.outcome_analyzer.analyze(
                price_analysis=price_analysis,
                exit_trading_day_index=(
                    exit_trading_day_index
                ),
            )
            for price_analysis in price_analyses
        )

        risk_grid = self.risk_grid_analyzer.analyze(
            outcomes=outcomes,
            call_thresholds=call_thresholds,
            put_thresholds=put_thresholds,
        )

        selection = self.strike_selector.select(
            risk_grid=risk_grid,
            expected_move_percent=expected_move_percent,
            policy=policy,
        )

        return HistoricalStrikeSelectionResult(
            outcomes=outcomes,
            risk_grid=risk_grid,
            selection=selection,
        )