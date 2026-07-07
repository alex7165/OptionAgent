from app.marketdata.models import MarketSnapshot


class AnalysisResult:
    def __init__(self, symbol: str, snapshot: MarketSnapshot):
        self.symbol = symbol
        self.snapshot = snapshot

    @property
    def summary(self) -> str:
        base = (
            f"{self.symbol}: "
            f"price {self.snapshot.quote.price} "
            f"{self.snapshot.quote.currency}"
        )

        if self.snapshot.earnings is None:
            return f"{base}, no earnings date available"

        return (
            f"{base}, "
            f"earnings {self.snapshot.earnings.report_date}, "
            f"{self.snapshot.earnings.timing}"
        )