from abc import ABC, abstractmethod
from datetime import date

from app.marketdata.models import EarningsEvent


class EarningsCalendarProvider(ABC):

    @abstractmethod
    def get_events(
        self,
        start_date: date,
        end_date: date,
    ) -> list[EarningsEvent]:
        pass