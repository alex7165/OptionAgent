from app.marketdata.models import Quote
from app.marketdata.provider import PriceProvider


class YahooPriceProvider(PriceProvider):

    def get_quote(self, symbol: str) -> Quote:
        raise NotImplementedError("YahooPriceProvider is not implemented yet.")