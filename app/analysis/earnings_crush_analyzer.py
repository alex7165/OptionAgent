from app.analysis.earnings_crush_candidate import EarningsCrushCandidate
from app.analysis.earnings_crush_rules import EarningsCrushRules
from app.analysis.expiration_selector import ExpirationSelector
from app.analysis.expected_move_analyzer import ExpectedMoveAnalyzer
from app.analysis.liquidity_analyzer import LiquidityAnalyzer
from app.analysis.option_data import OptionData
from app.analysis.strike_selector import StrikeSelector
from app.marketdata.barchart_volatility_provider import BarchartVolatilityProvider
from app.marketdata.optionstrat_provider import OptionStratProvider
from app.marketdata.service import MarketDataService
from app.analysis.strategy_selector import StrategySelector


class EarningsCrushAnalyzer:

    def __init__(self, market_data: MarketDataService):
        self.market_data = market_data
        self.option_provider = OptionStratProvider()
        self.volatility_provider = BarchartVolatilityProvider(headless=False)
        self.expiration_selector = ExpirationSelector(self.option_provider)
        self.expected_move_analyzer = ExpectedMoveAnalyzer()
        self.strike_selector = StrikeSelector()
        self.liquidity_analyzer = LiquidityAnalyzer()
        self.rules = EarningsCrushRules()

    def create_candidates(self, events):
        candidates = []

        for event in events:
            snapshot = self.market_data.get_snapshot(event.symbol)

            expiration = self.expiration_selector.select_earnings_week_expiration(
                event.symbol,
                event.report_date,
            )

            candidate = EarningsCrushCandidate(
                earnings_event=event,
                snapshot=snapshot,
                expiration=expiration,
            )

            if expiration is None:
                candidate.failed_rules.append("missing_earnings_week_expiration")
                candidates.append(candidate)
                continue

            chain = self.option_provider.get_expiration_chain(
                event.symbol,
                expiration,
            )

            if chain is None:
                candidate.failed_rules.append("missing_expiration_chain")
                candidates.append(candidate)
                continue

            expected_move = self.expected_move_analyzer.from_atm_straddle(
                chain,
                snapshot.quote.price,
            )

            if expected_move is None:
                candidate.failed_rules.append("missing_expected_move")
                candidates.append(candidate)
                continue

            candidate.expected_move = expected_move

            strategy = self.strategy_selector.select(
                defined_risk=True,
        )
            
            strategy = self.strategy_selector.select(
                defined_risk=True,
        )

            selection = self.strike_selector.select_by_expected_move(
                chain,
                expected_move,
                strategy=strategy,
        )

            candidate.strike_selection = selection

            candidate.option_data = OptionData(
                chain=chain,
                put=selection.put,
                call=selection.call,
                expected_move=expected_move,
                iv_rank=self.volatility_provider.get_iv_rank(event.symbol),
                iv_percentile=self.volatility_provider.get_iv_percentile(event.symbol),
            )

            candidate.liquidity = self.liquidity_analyzer.analyze(
                candidate.option_data
            )

            candidate = self.rules.evaluate(candidate)
            candidates.append(candidate)

        return candidates