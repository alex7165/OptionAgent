from app.analysis.earnings_analysis import EarningsAnalysis
from app.analysis.result import AnalysisResult


class EarningsAnalyzer:
    def __init__(self, market_data):
        self.market_data = market_data

    def analyze(self, symbol: str):
        market_snapshot = self.market_data.get_snapshot(symbol)
        earnings_event = market_snapshot.earnings

        earnings_analysis = EarningsAnalysis(
            has_earnings=earnings_event is not None,
            report_date=earnings_event.report_date if earnings_event else None,
            timing=earnings_event.timing if earnings_event else None,
        )

        return AnalysisResult(
            symbol=market_snapshot.symbol,
            snapshot=market_snapshot,
            earnings=earnings_analysis,
        )