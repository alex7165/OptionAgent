from app.analysis.result import AnalysisResult


class EarningsAnalyzer:
    def __init__(self, market_data):
        self.market_data = market_data

    def analyze(self, symbol: str):
        return AnalysisResult(summary=f"Analysis for {symbol} not implemented")