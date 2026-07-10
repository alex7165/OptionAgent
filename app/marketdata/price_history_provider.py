from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class DailyBar:
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


class PriceHistoryProvider(ABC):

    @abstractmethod
    def get_daily_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> tuple[DailyBar, ...]:
        """Return daily OHLCV bars in ascending date order."""
        raise NotImplementedError