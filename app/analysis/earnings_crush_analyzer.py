from app.analysis.earnings_crush_candidate import EarningsCrushCandidate
from app.marketdata.service import MarketDataService


class EarningsCrushAnalyzer:

    def __init__(self, market_data: MarketDataService):
        self.market_data = market_data

    def create_candidates(self, events):
        candidates = []

        for event in events:
            snapshot = self.market_data.get_snapshot(event.symbol)

            candidates.append(
                EarningsCrushCandidate(
                    earnings_event=event,
                    snapshot=snapshot,
                )
            )

        return candidates