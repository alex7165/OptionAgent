from datetime import date

import pytest

from app.analysis.historical_earnings_analysis import (
    HistoricalEarningsPriceSeries,
)
from app.analysis.reference_price_resolver import (
    FixedReferencePriceResolver,
    PreviousCloseReferencePriceResolver,
)
from app.marketdata.earnings_api_provider import (
    HistoricalEarningsReaction,
)
from app.marketdata.price_history_provider import (
    DailyBar,
    PriceHistoryProvider,
)


class RecordingPriceHistoryProvider(PriceHistoryProvider):

    def __init__(
        self,
        daily_bars: tuple[DailyBar, ...],
    ) -> None:
        self.daily_bars = daily_bars
        self.calls: list[dict[str, object]] = []

    def get_daily_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> tuple[DailyBar, ...]:
        self.calls.append(
            {
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date,
            }
        )

        return self.daily_bars


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


def make_daily_bar(
    bar_date: date,
    close: float,
) -> DailyBar:
    return DailyBar(
        date=bar_date,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1_000_000,
    )


def test_fixed_reference_price_resolver_returns_configured_price() -> None:
    resolver = FixedReferencePriceResolver(
        reference_price=97.5,
    )

    reference_price = resolver.resolve(
        make_price_series()
    )

    assert reference_price == 97.5


def test_previous_close_resolver_loads_price_history_before_earnings() -> None:
    provider = RecordingPriceHistoryProvider(
        daily_bars=(
            make_daily_bar(
                bar_date=date(2026, 4, 13),
                close=95.0,
            ),
            make_daily_bar(
                bar_date=date(2026, 4, 14),
                close=97.0,
            ),
            make_daily_bar(
                bar_date=date(2026, 4, 15),
                close=99.5,
            ),
        ),
    )
    resolver = PreviousCloseReferencePriceResolver(
        price_history_provider=provider,
        lookback_days=10,
    )

    reference_price = resolver.resolve(
        make_price_series()
    )

    assert provider.calls == [
        {
            "symbol": "NFLX",
            "start_date": date(2026, 4, 6),
            "end_date": date(2026, 4, 15),
        }
    ]
    assert reference_price == 99.5


def test_previous_close_resolver_uses_latest_available_trading_day() -> None:
    provider = RecordingPriceHistoryProvider(
        daily_bars=(
            make_daily_bar(
                bar_date=date(2026, 4, 15),
                close=101.0,
            ),
            make_daily_bar(
                bar_date=date(2026, 4, 13),
                close=96.0,
            ),
            make_daily_bar(
                bar_date=date(2026, 4, 14),
                close=98.0,
            ),
        ),
    )
    resolver = PreviousCloseReferencePriceResolver(
        price_history_provider=provider,
    )

    reference_price = resolver.resolve(
        make_price_series()
    )

    assert reference_price == 101.0


def test_previous_close_resolver_rejects_missing_price_history() -> None:
    provider = RecordingPriceHistoryProvider(
        daily_bars=(),
    )
    resolver = PreviousCloseReferencePriceResolver(
        price_history_provider=provider,
    )

    with pytest.raises(
        ValueError,
        match=(
            "No price history found before earnings date "
            "for NFLX on 2026-04-16"
        ),
    ):
        resolver.resolve(
            make_price_series()
        )


def test_previous_close_resolver_rejects_non_positive_close() -> None:
    provider = RecordingPriceHistoryProvider(
        daily_bars=(
            make_daily_bar(
                bar_date=date(2026, 4, 15),
                close=0.0,
            ),
        ),
    )
    resolver = PreviousCloseReferencePriceResolver(
        price_history_provider=provider,
    )

    with pytest.raises(
        ValueError,
        match="Previous close must be greater than zero",
    ):
        resolver.resolve(
            make_price_series()
        )


@pytest.mark.parametrize(
    "lookback_days",
    (
        0,
        -1,
    ),
)
def test_previous_close_resolver_rejects_invalid_lookback(
    lookback_days: int,
) -> None:
    provider = RecordingPriceHistoryProvider(
        daily_bars=(),
    )

    with pytest.raises(
        ValueError,
        match="lookback_days must be at least 1",
    ):
        PreviousCloseReferencePriceResolver(
            price_history_provider=provider,
            lookback_days=lookback_days,
        )