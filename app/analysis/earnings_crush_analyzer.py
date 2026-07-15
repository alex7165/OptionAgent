from dataclasses import dataclass
from typing import Protocol

from app.analysis.decision_report import DecisionReportBuilder
from app.analysis.earnings_crush_candidate import EarningsCrushCandidate
from app.analysis.earnings_crush_rules import EarningsCrushRules
from app.analysis.expiration_selector import ExpirationSelector
from app.analysis.expected_move_analyzer import ExpectedMoveAnalyzer
from app.analysis.historical_earnings_price_analyzer import (
    HistoricalEarningsPriceAnalysis,
)
from app.analysis.historical_strike_selector import (
    HistoricalStrikeSelectionPolicy,
)
from app.analysis.liquidity_analyzer import LiquidityAnalyzer
from app.analysis.liquidity_optimizer import LiquidityOptimizer
from app.analysis.option_data import OptionData
from app.analysis.strategy_selector import (
    StrategySelector,
    StrategyStrikeSelectionResult,
    StrikeSelectionSource,
)
from app.marketdata.barchart_volatility_provider import (
    BarchartVolatilityProvider,
)
from app.marketdata.optionstrat_provider import OptionStratProvider
from app.marketdata.service import MarketDataService


@dataclass(frozen=True, slots=True)
class HistoricalStrategySelectionInputs:
    price_analyses: tuple[HistoricalEarningsPriceAnalysis, ...]
    exit_trading_day_index: int
    call_thresholds: tuple[float, ...]
    put_thresholds: tuple[float, ...]
    policy: HistoricalStrikeSelectionPolicy


class HistoricalStrategySelectionInputsLoader(Protocol):

    def load(
        self,
        symbol: str,
    ) -> HistoricalStrategySelectionInputs | None:
        ...


class EarningsCrushAnalyzer:

    def __init__(
        self,
        market_data: MarketDataService,
        strategy_selector: StrategySelector | None = None,
        historical_inputs_loader: (
            HistoricalStrategySelectionInputsLoader | None
        ) = None,
    ) -> None:
        self.market_data = market_data
        self.option_provider = OptionStratProvider()
        self.volatility_provider = BarchartVolatilityProvider(
            headless=False
        )
        self.expiration_selector = ExpirationSelector(
            self.option_provider
        )
        self.expected_move_analyzer = ExpectedMoveAnalyzer()
        self.strategy_selector = strategy_selector or StrategySelector()
        self.historical_inputs_loader = historical_inputs_loader
        self.liquidity_analyzer = LiquidityAnalyzer()
        self.liquidity_optimizer = LiquidityOptimizer()
        self.rules = EarningsCrushRules()
        self.decision_report_builder = DecisionReportBuilder()

    def create_candidates(self, events):
        candidates = []

        for event in events:
            snapshot = self.market_data.get_snapshot(event.symbol)

            expiration = (
                self.expiration_selector
                .select_earnings_week_expiration(
                    event.symbol,
                    event.report_date,
                )
            )

            candidate = EarningsCrushCandidate(
                earnings_event=event,
                snapshot=snapshot,
                expiration=expiration,
            )

            if expiration is None:
                candidate.failed_rules.append(
                    "missing_earnings_week_expiration"
                )
                candidates.append(candidate)
                continue

            chain = self.option_provider.get_expiration_chain(
                event.symbol,
                expiration,
            )

            if chain is None:
                candidate.failed_rules.append(
                    "missing_expiration_chain"
                )
                candidates.append(candidate)
                continue

            expected_move = (
                self.expected_move_analyzer.from_atm_straddle(
                    chain,
                    snapshot.quote.price,
                )
            )

            if expected_move is None:
                candidate.failed_rules.append(
                    "missing_expected_move"
                )
                candidates.append(candidate)
                continue

            candidate.expected_move = expected_move

            strategy = self.strategy_selector.select(
                defined_risk=True,
            )

            historical_inputs = self._load_historical_inputs(
                event.symbol
            )

            if historical_inputs is None:
                selection_result = (
                    self._select_strikes_with_details(
                        chain=chain,
                        underlying_price=snapshot.quote.price,
                        expected_move=expected_move,
                        strategy=strategy,
                    )
                )
            else:
                selection_result = (
                    self._select_strikes_with_details(
                        chain=chain,
                        underlying_price=snapshot.quote.price,
                        expected_move=expected_move,
                        strategy=strategy,
                        price_analyses=(
                            historical_inputs.price_analyses
                        ),
                        exit_trading_day_index=(
                            historical_inputs.exit_trading_day_index
                        ),
                        call_thresholds=(
                            historical_inputs.call_thresholds
                        ),
                        put_thresholds=(
                            historical_inputs.put_thresholds
                        ),
                        policy=historical_inputs.policy,
                    )
                )

            selection = selection_result.strike_selection
            candidate.strike_selection_before_liquidity = selection
            candidate.strike_selection_source = selection_result.source
            candidate.historical_selection_result = (
                selection_result.historical_result
            )

            liquidity_optimizer = getattr(
                self,
                "liquidity_optimizer",
                None,
            )
            if liquidity_optimizer is not None:
                optimized_selection = liquidity_optimizer.optimize(
                    selection,
                    chain,
                )
                candidate.liquidity_optimization_reason = (
                    self._liquidity_optimization_reason(
                        selection,
                        optimized_selection,
                    )
                )
                selection = optimized_selection

            candidate.strike_selection = selection

            candidate.option_data = OptionData(
                chain=chain,
                put=selection.put,
                call=selection.call,
                expected_move=expected_move,
                iv_rank=self.volatility_provider.get_iv_rank(
                    event.symbol
                ),
                iv_percentile=(
                    self.volatility_provider.get_iv_percentile(
                        event.symbol
                    )
                ),
            )

            candidate.liquidity = self.liquidity_analyzer.analyze(
                candidate.option_data
            )

            report_builder = getattr(
                self,
                "decision_report_builder",
                DecisionReportBuilder(),
            )
            candidate.decision_report = report_builder.build(candidate)
            candidate = self.rules.evaluate(candidate)
            candidates.append(candidate)

        return candidates



    def _select_strikes_with_details(self, **kwargs):
        detailed_selector = getattr(
            self.strategy_selector,
            "select_strikes_with_details",
            None,
        )
        if detailed_selector is not None:
            return detailed_selector(**kwargs)

        selection = self.strategy_selector.select_strikes(**kwargs)
        source = (
            StrikeSelectionSource.HISTORICAL
            if kwargs.get("price_analyses") is not None
            else StrikeSelectionSource.EXPECTED_MOVE
        )
        return StrategyStrikeSelectionResult(
            strike_selection=selection,
            source=source,
        )

    @staticmethod
    def _liquidity_optimization_reason(
        before,
        after,
    ) -> str | None:
        changes = []

        if (
            before.put is not None
            and after.put is not None
            and before.put.strike != after.put.strike
        ):
            changes.append(
                "Put "
                f"{before.put.strike:g} → {after.put.strike:g} "
                f"(OI {before.put.open_interest or 0} → "
                f"{after.put.open_interest or 0})"
            )

        if (
            before.call is not None
            and after.call is not None
            and before.call.strike != after.call.strike
        ):
            changes.append(
                "Call "
                f"{before.call.strike:g} → {after.call.strike:g} "
                f"(OI {before.call.open_interest or 0} → "
                f"{after.call.open_interest or 0})"
            )

        return "; ".join(changes) or None

    def _load_historical_inputs(
        self,
        symbol: str,
    ) -> HistoricalStrategySelectionInputs | None:
        if self.historical_inputs_loader is None:
            return None

        return self.historical_inputs_loader.load(symbol)
