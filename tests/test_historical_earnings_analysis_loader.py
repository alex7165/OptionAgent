from datetime import date, timedelta

import pytest

from app.analysis.historical_earnings_analysis_loader import (
    HistoricalEarningsAnalysisLoader,
)
from app.analysis.historical_earnings_price_series_loader import (
    HistoricalEarningsPriceSeriesLoader,
)
from app.marketdata.earnings_api_provider import (
    HistoricalEarningsReaction,
)
from app.marketdata.price_history_provider import (
    DailyBar,
    PriceHistoryProvider,
)


class RecordingEarningsProvider:

    def __init__(
        self,
        reactions: tuple[HistoricalEarningsReaction, ...],
    ) -> None:
        self.reactions = reactions
        self.calls: list[str] = []

    def get_historical_reactions(
        self,
        symbol: str,
    ) -> tuple[HistoricalEarningsReaction, ...]:
        self.calls.append(symbol)
        return self.reactions


class RecordingPriceHistoryProvider(PriceHistoryProvider):

    def __init__(self) -> None:
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

        return (
            DailyBar(
                date=start_date,
                open=100.0,
                high=105.0,
                low=98.0,
                close=103.0,
                volume=1_000_000,
            ),
        )


def make_reaction(
    report_date: date,
) -> HistoricalEarningsReaction:
    return HistoricalEarningsReaction(
        report_date=report_date,
        symbol="NVDA",
        eps_surprise_percent=5.0,
        eps_yoy_percent=20.0,
        eps_beat=True,
        revenue_surprise_percent=3.0,
        revenue_yoy_percent=15.0,
        revenue_beat=True,
        reactions=(),
    )


def test_loads_price_series_for_all_earnings_events() -> None:
    first_reaction = make_reaction(
        report_date=date(2026, 2, 25),
    )
    second_reaction = make_reaction(
        report_date=date(2026, 5, 20),
    )

    earnings_provider = RecordingEarningsProvider(
        reactions=(
            first_reaction,
            second_reaction,
        )
    )
    price_history_provider = RecordingPriceHistoryProvider()

    loader = HistoricalEarningsAnalysisLoader(
        earnings_provider=earnings_provider,
        price_series_loader=HistoricalEarningsPriceSeriesLoader(
            price_history_provider=price_history_provider,
        ),
    )

    analysis = loader.load(
        symbol=" nvda ",
        end_date_resolver=lambda earnings: (
            earnings.report_date + timedelta(days=10)
        ),
    )

    assert earnings_provider.calls == ["NVDA"]

    assert price_history_provider.calls == [
        {
            "symbol": "NVDA",
            "start_date": date(2026, 2, 25),
            "end_date": date(2026, 3, 7),
        },
        {
            "symbol": "NVDA",
            "start_date": date(2026, 5, 20),
            "end_date": date(2026, 5, 30),
        },
    ]

    assert len(analysis.price_series) == 2

    assert analysis.price_series[0].earnings is first_reaction
    assert analysis.price_series[1].earnings is second_reaction

    assert analysis.price_series[0].daily_bars == (
        DailyBar(
            date=date(2026, 2, 25),
            open=100.0,
            high=105.0,
            low=98.0,
            close=103.0,
            volume=1_000_000,
        ),
    )

    assert analysis.outcomes == ()


def test_returns_empty_analysis_without_earnings_events() -> None:
    earnings_provider = RecordingEarningsProvider(
        reactions=(),
    )
    price_history_provider = RecordingPriceHistoryProvider()

    loader = HistoricalEarningsAnalysisLoader(
        earnings_provider=earnings_provider,
        price_series_loader=HistoricalEarningsPriceSeriesLoader(
            price_history_provider=price_history_provider,
        ),
    )

    analysis = loader.load(
        symbol="NVDA",
        end_date_resolver=lambda earnings: earnings.report_date,
    )

    assert earnings_provider.calls == ["NVDA"]
    assert price_history_provider.calls == []
    assert analysis.price_series == ()
    assert analysis.outcomes == ()


def test_rejects_empty_symbol_without_loading_data() -> None:
    earnings_provider = RecordingEarningsProvider(
        reactions=(),
    )
    price_history_provider = RecordingPriceHistoryProvider()

    loader = HistoricalEarningsAnalysisLoader(
        earnings_provider=earnings_provider,
        price_series_loader=HistoricalEarningsPriceSeriesLoader(
            price_history_provider=price_history_provider,
        ),
    )

    with pytest.raises(
        ValueError,
        match="symbol must not be empty",
    ):
        loader.load(
            symbol=" ",
            end_date_resolver=lambda earnings: earnings.report_date,
        )

    assert earnings_provider.calls == []
    assert price_history_provider.calls == []

class WarmableRecordingPriceHistoryProvider(RecordingPriceHistoryProvider):

    def __init__(self) -> None:
        super().__init__()
        self.warm_requests: list[tuple[tuple[str, date, date], ...]] = []

    def warm_cache(self, requests) -> None:
        self.warm_requests.append(tuple(requests))


def test_warms_price_history_cache_before_loading_series() -> None:
    reaction = make_reaction(report_date=date(2026, 5, 20))
    earnings_provider = RecordingEarningsProvider(reactions=(reaction,))
    price_history_provider = WarmableRecordingPriceHistoryProvider()
    loader = HistoricalEarningsAnalysisLoader(
        earnings_provider=earnings_provider,
        price_series_loader=HistoricalEarningsPriceSeriesLoader(
            price_history_provider=price_history_provider,
        ),
    )

    loader.load(
        symbol="NVDA",
        end_date_resolver=lambda earnings: date(2026, 5, 22),
    )

    assert price_history_provider.warm_requests == [
        (("NVDA", date(2026, 5, 20), date(2026, 5, 22)),)
    ]
