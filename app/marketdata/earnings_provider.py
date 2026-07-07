from abc import ABC, abstractmethod

from app.marketdata.models import EarningsEvent


class EarningsProvider(ABC):

    @abstractmethod
    def get_earnings(self, symbol: str) -> EarningsEvent | None:
        pass