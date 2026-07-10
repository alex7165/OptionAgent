from datetime import date

import pytest

from app.analysis.price_series_analyzer import PriceSeriesAnalyzer
from app.marketdata.price_history_provider import DailyBar


def make_daily_bars() -> tuple[DailyBar, ...]:
    return (
        DailyBar(
            date=date(2026, 4, 17),
            open=96.0,
            high=102.0,
            low=94.0,
            close=100.0,
            volume=1_000_000,
        ),
        DailyBar(
            date=date(2026, 4, 20),
            open=100.0,
            high=108.0,
            low=97.0,
            close=104.0,
            volume=900_000,
        ),
        DailyBar(
            date=date(2026, 4, 21),
            open=104.0,
            high=106.0,
            low=92.0,
            close=95.0,
            volume=800_000,
        ),
    )


def test_analyzes_complete_price_series() -> None:
    analysis = PriceSeriesAnalyzer().analyze(
        daily_bars=make_daily_bars(),
        reference_price=100.0,
    )

    assert analysis.reference_price == 100.0
    assert analysis.first_date == date(2026, 4, 17)
    assert analysis.last_date == date(2026, 4, 21)
    assert analysis.first_open == 96.0
    assert analysis.first_close == 100.0
    assert analysis.last_close == 95.0
    assert analysis.highest_high == 108.0
    assert analysis.lowest_low == 92.0
    assert analysis.max_gain_percent == pytest.approx(8.0)
    assert analysis.max_loss_percent == pytest.approx(-8.0)


def test_uses_explicit_reference_price() -> None:
    analysis = PriceSeriesAnalyzer().analyze(
        daily_bars=make_daily_bars(),
        reference_price=80.0,
    )

    assert analysis.max_gain_percent == pytest.approx(35.0)
    assert analysis.max_loss_percent == pytest.approx(15.0)


def test_rejects_empty_price_series() -> None:
    with pytest.raises(
        ValueError,
        match="daily_bars must not be empty",
    ):
        PriceSeriesAnalyzer().analyze(
            daily_bars=(),
            reference_price=100.0,
        )


@pytest.mark.parametrize(
    "reference_price",
    [
        0.0,
        -1.0,
    ],
)
def test_rejects_invalid_reference_price(
    reference_price: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="reference_price must be greater than zero",
    ):
        PriceSeriesAnalyzer().analyze(
            daily_bars=make_daily_bars(),
            reference_price=reference_price,
        )


def test_rejects_unsorted_price_series() -> None:
    daily_bars = (
        DailyBar(
            date=date(2026, 4, 20),
            open=100.0,
            high=105.0,
            low=98.0,
            close=103.0,
            volume=1_000_000,
        ),
        DailyBar(
            date=date(2026, 4, 17),
            open=96.0,
            high=102.0,
            low=94.0,
            close=100.0,
            volume=900_000,
        ),
    )

    with pytest.raises(
        ValueError,
        match="daily_bars must be ordered by ascending unique date",
    ):
        PriceSeriesAnalyzer().analyze(
            daily_bars=daily_bars,
            reference_price=100.0,
        )


def test_rejects_duplicate_dates() -> None:
    daily_bars = (
        DailyBar(
            date=date(2026, 4, 17),
            open=96.0,
            high=102.0,
            low=94.0,
            close=100.0,
            volume=1_000_000,
        ),
        DailyBar(
            date=date(2026, 4, 17),
            open=100.0,
            high=105.0,
            low=98.0,
            close=103.0,
            volume=900_000,
        ),
    )

    with pytest.raises(
        ValueError,
        match="daily_bars must be ordered by ascending unique date",
    ):
        PriceSeriesAnalyzer().analyze(
            daily_bars=daily_bars,
            reference_price=100.0,
        )