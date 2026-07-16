from datetime import date

import pandas as pd
import pytest

from app.marketdata.yahoo_price_history_provider import YahooPriceHistoryProvider


def test_returns_daily_bars_and_requests_inclusive_end():
    captured = {}
    frame = pd.DataFrame(
        {
            "Open": [100.0, 101.0],
            "High": [102.0, 103.0],
            "Low": [99.0, 100.0],
            "Close": [101.0, 102.0],
            "Volume": [1000, 1200],
        },
        index=pd.to_datetime(["2026-07-14", "2026-07-15"]),
    )

    def fake_download(symbol, **kwargs):
        captured["symbol"] = symbol
        captured.update(kwargs)
        return frame

    bars = YahooPriceHistoryProvider(downloader=fake_download).get_daily_bars(
        "c",
        date(2026, 7, 14),
        date(2026, 7, 15),
    )

    assert captured["symbol"] == "C"
    assert captured["start"] == "2026-07-14"
    assert captured["end"] == "2026-07-16"
    assert [bar.date for bar in bars] == [date(2026, 7, 14), date(2026, 7, 15)]
    assert bars[1].close == 102.0
    assert bars[1].volume == 1200


def test_returns_empty_tuple_when_yahoo_has_no_data():
    provider = YahooPriceHistoryProvider(
        downloader=lambda *args, **kwargs: pd.DataFrame()
    )

    bars = provider.get_daily_bars(
        "UNKNOWN",
        date(2026, 7, 14),
        date(2026, 7, 15),
    )

    assert bars == ()


def test_rejects_reversed_date_range():
    provider = YahooPriceHistoryProvider(
        downloader=lambda *args, **kwargs: pd.DataFrame()
    )

    with pytest.raises(ValueError, match="end_date"):
        provider.get_daily_bars(
            "C",
            date(2026, 7, 15),
            date(2026, 7, 14),
        )
