from app.marketdata.models import MarketSnapshot


class AnalysisResult:
    def __init__(self, symbol: str, snapshot: MarketSnapshot):
        self.symbol = symbol
        self.snapshot = snapshot

    @property
    def summary(self) -> str:
        if self.snapshot.earnings is None:
            return (
                f"{self.symbol}: "
                f"price {self.snapshot.quote.price} "
                f"{self.snapshot.quote.currency}, "
                "no earnings date available"
            )

        return (
            f"{self.symbol}: "
            f"price {self.snapshot.quote.price} "
            f"{self.snapshot.quote.currency}"
        )