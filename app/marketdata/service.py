from app.marketdata.earnings_provider import EarningsProvider
from app.marketdata.models import MarketSnapshot
from app.marketdata.provider import PriceProvider


class MarketDataService:

    def __init__(
        self,
        price_provider: PriceProvider,
        earnings_provider: EarningsProvider | None = None,
    ):
        self.price_provider = price_provider
        self.earnings_provider = earnings_provider

    def get_snapshot(self, symbol: str) -> MarketSnapshot:
        quote = self.price_provider.get_quote(symbol)
        earnings = None

        if self.earnings_provider is not None:
            earnings = self.earnings_provider.get_earnings(symbol)

        return MarketSnapshot(
            symbol=symbol.upper(),
            quote=quote,
            earnings=earnings,
        )