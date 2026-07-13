from app.analysis.daily_move_analyzer import DailyMoveAnalyzer
from app.analysis.earnings_crush_analyzer import EarningsCrushAnalyzer
from app.analysis.historical_earnings_analysis_analyzer import (
    HistoricalEarningsAnalysisAnalyzer,
)
from app.analysis.historical_earnings_analysis_loader import (
    HistoricalEarningsAnalysisLoader,
)
from app.analysis.historical_earnings_price_analyzer import (
    HistoricalEarningsPriceAnalyzer,
)
from app.analysis.historical_earnings_price_series_loader import (
    HistoricalEarningsPriceSeriesLoader,
)
from app.analysis.historical_outcome_analyzer import (
    HistoricalOutcomeAnalyzer,
)
from app.analysis.historical_price_statistics_analyzer import (
    HistoricalPriceStatisticsAnalyzer,
)
from app.analysis.historical_strategy_selection_inputs_loader import (
    HistoricalStrategySelectionInputsLoader,
)
from app.analysis.historical_strategy_selector_adapter import (
    HistoricalStrategySelectorAdapter,
)
from app.analysis.historical_strike_adjusted_selector import (
    HistoricalStrikeAdjustedSelector,
)
from app.analysis.historical_strike_risk_analyzer import (
    HistoricalStrikeRiskAnalyzer,
)
from app.analysis.historical_strike_risk_grid_analyzer import (
    HistoricalStrikeRiskGridAnalyzer,
)
from app.analysis.historical_strike_selection_service import (
    HistoricalStrikeSelectionService,
)
from app.analysis.historical_strike_selector import (
    HistoricalStrikeSelectionPolicy,
    HistoricalStrikeSelector,
)
from app.analysis.price_series_analyzer import PriceSeriesAnalyzer
from app.analysis.reference_price_resolver import (
    PreviousCloseReferencePriceResolver,
)
from app.analysis.strategy_selector import StrategySelector
from app.analysis.strike_selector import StrikeSelector
from app.marketdata.earnings_api_provider import EarningsApiProvider
from app.marketdata.massive_price_history_provider import (
    MassivePriceHistoryProvider,
)
from app.marketdata.service import MarketDataService


class EarningsCrushAnalyzerFactory:

    def create(
        self,
        market_data: MarketDataService,
    ) -> EarningsCrushAnalyzer:
        try:
            return self._create_historical_analyzer(market_data)
        except ValueError as error:
            if "is not configured" not in str(error):
                raise

            return EarningsCrushAnalyzer(market_data)

    @staticmethod
    def _create_historical_analyzer(
        market_data: MarketDataService,
    ) -> EarningsCrushAnalyzer:
        price_history_provider = MassivePriceHistoryProvider()

        analysis_loader = HistoricalEarningsAnalysisLoader(
            earnings_provider=EarningsApiProvider(),
            price_series_loader=(
                HistoricalEarningsPriceSeriesLoader(
                    price_history_provider=price_history_provider,
                )
            ),
        )

        analysis_analyzer = HistoricalEarningsAnalysisAnalyzer(
            price_analyzer=HistoricalEarningsPriceAnalyzer(
                price_series_analyzer=PriceSeriesAnalyzer(),
                daily_move_analyzer=DailyMoveAnalyzer(),
            ),
            statistics_analyzer=(
                HistoricalPriceStatisticsAnalyzer()
            ),
        )

        historical_inputs_loader = (
            HistoricalStrategySelectionInputsLoader(
                analysis_loader=analysis_loader,
                analysis_analyzer=analysis_analyzer,
                reference_price_resolver=(
                    PreviousCloseReferencePriceResolver(
                        price_history_provider=price_history_provider,
                    )
                ),
                exit_trading_day_index=3,
                call_thresholds=(
                    5.0,
                    7.5,
                    10.0,
                    12.5,
                    15.0,
                    20.0,
                    25.0,
                    30.0,
                    40.0,
                ),
                put_thresholds=(
                    -5.0,
                    -7.5,
                    -10.0,
                    -12.5,
                    -15.0,
                    -20.0,
                    -25.0,
                    -30.0,
                    -40.0,
                ),
                policy=HistoricalStrikeSelectionPolicy(
                    max_finish_outside_probability=0.10,
                ),
            )
        )

        strike_selector = StrikeSelector()
        historical_adapter = HistoricalStrategySelectorAdapter(
            historical_selection_service=(
                HistoricalStrikeSelectionService(
                    outcome_analyzer=HistoricalOutcomeAnalyzer(),
                    risk_grid_analyzer=(
                        HistoricalStrikeRiskGridAnalyzer(
                            strike_risk_analyzer=(
                                HistoricalStrikeRiskAnalyzer()
                            )
                        )
                    ),
                    strike_selector=HistoricalStrikeSelector(),
                )
            ),
            adjusted_selector=HistoricalStrikeAdjustedSelector(
                strike_selector=strike_selector,
            ),
        )

        strategy_selector = StrategySelector(
            strike_selector=strike_selector,
            historical_adapter=historical_adapter,
        )

        return EarningsCrushAnalyzer(
            market_data=market_data,
            strategy_selector=strategy_selector,
            historical_inputs_loader=historical_inputs_loader,
        )
