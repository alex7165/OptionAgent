from app.marketdata.models import Quote
from app.marketdata.provider import PriceProvider


class DummyPriceProvider(PriceProvider):

    def get_quote(self, symbol: str) -> Quote:
        return Quote(
            symbol=symbol.upper(),
            price=100.0,
            currency="USD",
            source="dummy",
        )