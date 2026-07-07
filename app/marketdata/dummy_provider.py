from app.marketdata.models import StockData
from app.marketdata.provider import StockDataProvider


class DummyStockDataProvider(StockDataProvider):

    def get_stock(self, symbol: str) -> StockData:
        return StockData(
            symbol=symbol.upper(),
            price=100.0,
            currency="USD",
            source="dummy",
        )