from datetime import date

import pandas as pd

from app.marketdata.historical_earnings_date_provider import (
    YahooHistoricalEarningsDateProvider,
)


def test_returns_sorted_unique_dates_from_yahoo_frame():
    frame = pd.DataFrame(
        index=pd.Index([
            pd.Timestamp("2025-07-15 08:00:00-04:00"),
            pd.Timestamp("2024-07-16"),
            pd.Timestamp("2025-07-15"),
        ])
    )
    provider = YahooHistoricalEarningsDateProvider(
        loader=lambda symbol: frame
    )

    assert provider.get_report_dates("gs") == (
        date(2024, 7, 16),
        date(2025, 7, 15),
    )


def test_returns_empty_tuple_when_yahoo_has_no_data():
    provider = YahooHistoricalEarningsDateProvider(
        loader=lambda symbol: None
    )

    assert provider.get_report_dates("GS") == ()
