from datetime import date

from app.marketdata.earnings_calendar_provider import EarningsCalendarProvider
from app.marketdata.models import EarningsEvent


class FinvizEarningsCalendarProvider(EarningsCalendarProvider):

    def get_events(
        self,
        start_date: date,
        end_date: date,
    ) -> list[EarningsEvent]:
        raise NotImplementedError(
            "FinvizEarningsCalendarProvider is not implemented yet."
        )