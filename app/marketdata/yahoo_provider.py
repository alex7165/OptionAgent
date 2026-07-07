import yfinance as yf

from app.marketdata.models import Quote
from app.marketdata.provider import PriceProvider


class YahooPriceProvider(PriceProvider):

    def get_quote(self, symbol: str) -> Quote:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info

        return Quote(
            symbol=symbol.upper(),
            price=float(info["lastPrice"]),
            currency=info.get("currency", "USD"),
            source="yahoo",
        )