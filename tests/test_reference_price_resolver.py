from datetime import date

from app.analysis.historical_earnings_analysis import (
    HistoricalEarningsPriceSeries,
)
from app.analysis.reference_price_resolver import (
    FixedReferencePriceResolver,
)
from app.marketdata.earnings_api_provider import (
    HistoricalEarningsReaction,
)
from app.marketdata.price_history_provider import DailyBar


def make_price_series() -> HistoricalEarningsPriceSeries:
    return HistoricalEarningsPriceSeries(
        earnings=HistoricalEarningsReaction(
            report_date=date(2026, 4, 16),
            symbol="NFLX",
            eps_surprise_percent=5.0,
            eps_yoy_percent=10.0,
            eps_beat=True,
            revenue_surprise_percent=2.0,
            revenue_yoy_percent=8.0,
            revenue_beat=True,
            reactions=(),
        ),
        daily_bars=(
            DailyBar(
                date=date(2026, 4, 17),
                open=100.0,
                high=105.0,
                low=95.0,
                close=102.0,
                volume=1_000_000,
            ),
        ),
    )


def test_fixed_reference_price_resolver_returns_configured_price() -> None:
    resolver = FixedReferencePriceResolver(
        reference_price=97.5,
    )

    reference_price = resolver.resolve(
        make_price_series()
    )

    assert reference_price == 97.5