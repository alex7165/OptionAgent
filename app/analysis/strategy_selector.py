from app.analysis.expected_move import ExpectedMove
from app.analysis.historical_earnings_price_analyzer import (
    HistoricalEarningsPriceAnalysis,
)
from app.analysis.historical_strike_selector import (
    HistoricalStrikeSelectionPolicy,
)
from app.analysis.historical_strategy_selector_adapter import (
    HistoricalStrategySelectorAdapter,
)
from app.analysis.liquidity_optimizer import LiquidityOptimizer
from app.analysis.strategy import Strategy
from app.analysis.strike_selection import StrikeSelection
from app.analysis.strike_selector import StrikeSelector
from app.marketdata.models import ExpirationChain


class StrategySelector:

    def __init__(
        self,
        strike_selector: StrikeSelector | None = None,
        historical_adapter: (
            HistoricalStrategySelectorAdapter | None
        ) = None,
        liquidity_optimizer: LiquidityOptimizer | None = None,
    ) -> None:
        self.strike_selector = strike_selector or StrikeSelector()
        self.historical_adapter = historical_adapter
        self.liquidity_optimizer = (
            liquidity_optimizer or LiquidityOptimizer()
        )

    def select(
        self,
        defined_risk: bool,
    ) -> Strategy:
        if defined_risk:
            return Strategy.IRON_CONDOR

        return Strategy.SHORT_STRANGLE

    def select_strikes(
        self,
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
    ) -> StrikeSelection:
        if self.historical_adapter is None:
            selection = self.strike_selector.select_by_expected_move(
                chain=chain,
                expected_move=expected_move,
                strategy=strategy,
            )
            return self.liquidity_optimizer.optimize(
                selection=selection,
                chain=chain,
                underlying_price=underlying_price,
            )

        if price_analyses is None:
            raise ValueError(
                "price_analyses are required when historical_adapter is set"
            )

        if exit_trading_day_index is None:
            raise ValueError(
                "exit_trading_day_index is required when "
                "historical_adapter is set"
            )

        if call_thresholds is None:
            raise ValueError(
                "call_thresholds are required when historical_adapter is set"
            )

        if put_thresholds is None:
            raise ValueError(
                "put_thresholds are required when historical_adapter is set"
            )

        if policy is None:
            raise ValueError(
                "policy is required when historical_adapter is set"
            )

        result = self.historical_adapter.select(
            chain=chain,
            underlying_price=underlying_price,
            expected_move=expected_move,
            price_analyses=price_analyses,
            exit_trading_day_index=exit_trading_day_index,
            call_thresholds=call_thresholds,
            put_thresholds=put_thresholds,
            policy=policy,
            strategy=strategy,
        )

        return self.liquidity_optimizer.optimize(
            selection=result.adjusted_selection.strike_selection,
            chain=chain,
            underlying_price=underlying_price,
        )
