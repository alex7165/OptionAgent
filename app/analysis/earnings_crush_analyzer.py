from app.analysis.earnings_crush_candidate import EarningsCrushCandidate
from app.analysis.earnings_crush_rules import EarningsCrushRules
from app.analysis.liquidity_analyzer import LiquidityAnalyzer
from app.marketdata.service import MarketDataService


class EarningsCrushAnalyzer:

    def __init__(self, market_data: MarketDataService):
        self.market_data = market_data
        self.rules = EarningsCrushRules()
        self.liquidity_analyzer = LiquidityAnalyzer()

    def create_candidates(self, events):
        candidates = []

        for event in events:
            snapshot = self.market_data.get_snapshot(event.symbol)
            option_data = self.market_data.get_option_data(event.symbol)

            candidate = EarningsCrushCandidate(
                earnings_event=event,
                snapshot=snapshot,
                option_data=option_data,
            )

            candidate.liquidity = self.liquidity_analyzer.analyze(
                option_data
            )

            candidate = self.rules.evaluate(candidate)

            candidates.append(candidate)

        return candidates