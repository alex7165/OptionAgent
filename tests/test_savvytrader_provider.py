from datetime import date
import pytest

from app.marketdata.savvytrader_earnings_calendar_provider import (
    SavvyTraderEarningsCalendarProvider,
)

@pytest.mark.integration

def test_savvytrader_returns_events():
    provider = SavvyTraderEarningsCalendarProvider()

    events = provider.get_events(
        date(2026, 7, 6),
        date(2026, 7, 10),
    )

    assert len(events) > 0
    assert events[0].symbol
    assert events[0].report_date
    assert events[0].source == "savvytrader"