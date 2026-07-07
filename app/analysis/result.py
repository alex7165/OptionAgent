from dataclasses import dataclass

from app.analysis.earnings_analysis import EarningsAnalysis
from app.analysis.earnings_status import EarningsStatus
from app.marketdata.models import MarketSnapshot


@dataclass
class AnalysisResult:
    symbol: str
    snapshot: MarketSnapshot
    earnings: EarningsAnalysis | None = None

    @property
    def summary(self) -> str:
        base = (
            f"{self.symbol}: "
            f"price {self.snapshot.quote.price} "
            f"{self.snapshot.quote.currency}"
        )

        if self.earnings is None:
            return base

        if self.earnings.status == EarningsStatus.NOT_AVAILABLE:
            return f"{base}, no earnings date available"

        return (
            f"{base}, "
            f"earnings {self.earnings.report_date}, "
            f"{self.earnings.timing}"
        )