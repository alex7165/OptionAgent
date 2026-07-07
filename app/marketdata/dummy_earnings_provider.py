from datetime import date

from app.marketdata.earnings_provider import EarningsProvider
from app.marketdata.models import EarningsEvent


DUMMY_EARNINGS_DATE = date(2026, 1, 1)


class DummyEarningsProvider(EarningsProvider):

    def get_earnings(self, symbol: str) -> EarningsEvent | None:
        return EarningsEvent(
            symbol=symbol.upper(),
            report_date=DUMMY_EARNINGS_DATE,
            timing="after market close",
            source="dummy",
        )
