from datetime import date

import requests

from app.marketdata.earnings_calendar_provider import EarningsCalendarProvider
from app.marketdata.models import EarningsEvent


class SavvyTraderEarningsCalendarProvider(EarningsCalendarProvider):

    BASE_URL = "https://api.savvytrader.com/pricing/assets/earnings/calendar"

    def get_events(
        self,
        start_date: date,
        end_date: date,
    ) -> list[EarningsEvent]:
        response = requests.get(
            self.BASE_URL,
            params={
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            timeout=10,
        )
        response.raise_for_status()

        data = response.json()

        return [self._to_event(item) for item in data]

    def _to_event(self, item: dict) -> EarningsEvent:
        return EarningsEvent(
            symbol=item["symbol"],
            report_date=date.fromisoformat(item["earningsDate"]),
            timing=item.get("earningsTime"),
            source="savvytrader",
        )