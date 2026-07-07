from abc import ABC, abstractmethod

from app.marketdata.models import StockData


class StockDataProvider(ABC):

    @abstractmethod
    def get_stock(self, symbol: str) -> StockData:
        pass