from abc import ABC, abstractmethod


class VolatilityProvider(ABC):

    @abstractmethod
    def get_iv_rank(self, symbol: str) -> float | None:
        pass

    @abstractmethod
    def get_iv_percentile(self, symbol: str) -> float | None:
        pass