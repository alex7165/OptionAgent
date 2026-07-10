from datetime import date

import pytest

from app.marketdata.massive_price_history_provider import (
    MassivePriceHistoryProvider,
)


class DummyMassiveClient:

    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.calls: list[dict] = []

    def get(
        self,
        path: str,
        params: dict | None = None,
    ) -> dict:
        self.calls.append(
            {
                "path": path,
                "params": params,
            }
        )

        return self.payload


def test_get_daily_bars_returns_normalized_history() -> None:
    client = DummyMassiveClient(
        {
            "adjusted": False,
            "results": [
                {
                    "o": 180.0,
                    "h": 185.0,
                    "l": 178.0,
                    "c": 183.5,
                    "v": 42_000_000,
                    "t": 1783555200000,
                },
                {
                    "o": 184.0,
                    "h": 188.0,
                    "l": 182.5,
                    "c": 187.0,
                    "v": 38_000_000,
                    "t": 1783641600000,
                },
            ],
            "status": "OK",
        }
    )

    provider = MassivePriceHistoryProvider(client=client)

    bars = provider.get_daily_bars(
        symbol=" nvda ",
        start_date=date(2026, 7, 9),
        end_date=date(2026, 7, 10),
    )

    assert client.calls == [
        {
            "path": (
                "/v2/aggs/ticker/NVDA/range/1/day/"
                "2026-07-09/2026-07-10"
            ),
            "params": {
                "adjusted": "false",
                "sort": "asc",
                "limit": 50_000,
            },
        }
    ]

    assert len(bars) == 2

    assert bars[0].date == date(2026, 7, 9)
    assert bars[0].open == 180.0
    assert bars[0].high == 185.0
    assert bars[0].low == 178.0
    assert bars[0].close == 183.5
    assert bars[0].volume == 42_000_000

    assert bars[1].date == date(2026, 7, 10)
    assert bars[1].close == 187.0


def test_get_daily_bars_returns_empty_tuple_without_results() -> None:
    client = DummyMassiveClient(
        {
            "status": "OK",
            "resultsCount": 0,
        }
    )

    provider = MassivePriceHistoryProvider(client=client)

    bars = provider.get_daily_bars(
        symbol="NVDA",
        start_date=date(2026, 7, 4),
        end_date=date(2026, 7, 5),
    )

    assert bars == ()


def test_rejects_empty_symbol() -> None:
    provider = MassivePriceHistoryProvider(
        client=DummyMassiveClient({})
    )

    with pytest.raises(
        ValueError,
        match="symbol must not be empty",
    ):
        provider.get_daily_bars(
            symbol=" ",
            start_date=date(2026, 7, 9),
            end_date=date(2026, 7, 10),
        )


def test_rejects_invalid_date_range() -> None:
    provider = MassivePriceHistoryProvider(
        client=DummyMassiveClient({})
    )

    with pytest.raises(
        ValueError,
        match="start_date must be before or equal to end_date",
    ):
        provider.get_daily_bars(
            symbol="NVDA",
            start_date=date(2026, 7, 10),
            end_date=date(2026, 7, 9),
        )


def test_rejects_invalid_results() -> None:
    provider = MassivePriceHistoryProvider(
        client=DummyMassiveClient(
            {
                "status": "OK",
                "results": {},
            }
        )
    )

    with pytest.raises(
        ValueError,
        match="Massive API returned invalid daily bar results",
    ):
        provider.get_daily_bars(
            symbol="NVDA",
            start_date=date(2026, 7, 9),
            end_date=date(2026, 7, 10),
        )