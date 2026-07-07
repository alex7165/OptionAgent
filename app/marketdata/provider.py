from abc import ABC, abstractmethod

from app.marketdata.models import Quote


class PriceProvider(ABC):

    @abstractmethod
    def get_quote(self, symbol: str) -> Quote:
        pass