from app.marketdata.models import MarketSnapshot


class AnalysisResult:
    def __init__(self, symbol: str, summary: str, snapshot: MarketSnapshot):
        self.symbol = symbol
        self.summary = summary
        self.snapshot = snapshot