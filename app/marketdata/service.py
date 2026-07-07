from app.marketdata.models import MarketSnapshot
from app.marketdata.provider import PriceProvider


class MarketDataService:

    def __init__(self, price_provider: PriceProvider):
        self.price_provider = price_provider

    def get_snapshot(self, symbol: str) -> MarketSnapshot:
        quote = self.price_provider.get_quote(symbol)

        return MarketSnapshot(
            symbol=symbol.upper(),
            quote=quote,
        )