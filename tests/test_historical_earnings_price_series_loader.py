from datetime import date

import pytest

from app.analysis.historical_earnings_price_series_loader import (
    HistoricalEarningsPriceSeriesLoader,
)
from app.marketdata.earnings_api_provider import (
    EarningsReactionDay,
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


def make_earnings_reaction() -> HistoricalEarningsReaction:
    return HistoricalEarningsReaction(
        report_date=date(2026, 4, 16),
        symbol="NFLX",
        eps_surprise_percent=-7.9,
        eps_yoy_percent=-89.4,
        eps_beat=False,
        revenue_surprise_percent=0.6,
        revenue_yoy_percent=16.2,
        revenue_beat=True,
        reactions=(
            EarningsReactionDay(
                date=date(2026, 4, 17),
                open=96.37,
                high=98.74,
                low=95.10,
                close=97.31,
                volume=125_958_732,
                price_change_percent=-9.72,
            ),
        ),
    )


def test_loads_complete_daily_price_series() -> None:
    daily_bars = (
        DailyBar(
            date=date(2026, 4, 16),
            open=107.50,
            high=108.20,
            low=106.10,
            close=107.79,
            volume=34_000_000,
        ),
        DailyBar(
            date=date(2026, 4, 17),
            open=96.37,
            high=98.74,
            low=95.10,
            close=97.31,
            volume=125_958_732,
        ),
        DailyBar(
            date=date(2026, 4, 20),
            open=97.14,
            high=97.60,
            low=93.54,
            close=94.83,
            volume=63_298_300,
        ),
    )
    provider = RecordingPriceHistoryProvider(
        daily_bars=daily_bars,
    )
    loader = HistoricalEarningsPriceSeriesLoader(
        price_history_provider=provider,
    )
    earnings = make_earnings_reaction()

    series = loader.load(
        earnings=earnings,
        end_date=date(2026, 4, 24),
    )

    assert provider.calls == [
        {
            "symbol": "NFLX",
            "start_date": date(2026, 4, 16),
            "end_date": date(2026, 4, 24),
        }
    ]
    assert series.earnings is earnings
    assert series.daily_bars == daily_bars


def test_preserves_empty_price_series() -> None:
    provider = RecordingPriceHistoryProvider(
        daily_bars=(),
    )
    loader = HistoricalEarningsPriceSeriesLoader(
        price_history_provider=provider,
    )
    earnings = make_earnings_reaction()

    series = loader.load(
        earnings=earnings,
        end_date=date(2026, 4, 24),
    )

    assert series.earnings is earnings
    assert series.daily_bars == ()


def test_rejects_end_date_before_report_date() -> None:
    provider = RecordingPriceHistoryProvider(
        daily_bars=(),
    )
    loader = HistoricalEarningsPriceSeriesLoader(
        price_history_provider=provider,
    )

    with pytest.raises(
        ValueError,
        match=(
            "end_date must be on or after "
            "the earnings report date"
        ),
    ):
        loader.load(
            earnings=make_earnings_reaction(),
            end_date=date(2026, 4, 15),
        )

    assert provider.calls == []