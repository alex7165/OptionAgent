from app.analysis.result import AnalysisResult


class EarningsAnalyzer:
    def __init__(self, market_data):
        self.market_data = market_data

    def analyze(self, symbol: str):
        market_snapshot = self.market_data.get_snapshot(symbol)

        return AnalysisResult(
            symbol=market_snapshot.symbol,
            snapshot=market_snapshot,
        )