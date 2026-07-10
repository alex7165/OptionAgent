from datetime import date

from app.marketdata.price_history_provider import DailyBar


def test_daily_bar_stores_ohlcv_data() -> None:
    bar = DailyBar(
        date=date(2026, 7, 9),
        open=180.0,
        high=185.0,
        low=178.0,
        close=183.5,
        volume=42_000_000,
    )

    assert bar.date == date(2026, 7, 9)
    assert bar.open == 180.0
    assert bar.high == 185.0
    assert bar.low == 178.0
    assert bar.close == 183.5
    assert bar.volume == 42_000_000