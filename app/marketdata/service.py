from app.marketdata.models import StockData
from app.marketdata.provider import StockDataProvider


class MarketDataService:

    def __init__(self, stock_provider: StockDataProvider):
        self.stock_provider = stock_provider

    def get_stock(self, symbol: str) -> StockData:
        return self.stock_provider.get_stock(symbol)