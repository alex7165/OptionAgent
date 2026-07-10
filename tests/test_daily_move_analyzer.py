from datetime import date

import pytest

from app.analysis.daily_move_analyzer import DailyMoveAnalyzer
from app.marketdata.price_history_provider import DailyBar


def make_daily_bar(
    bar_date: date,
    open_price: float,
    high_price: float,
    low_price: float,
    close_price: float,
) -> DailyBar:
    return DailyBar(
        date=bar_date,
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume=1_000_000,
    )


def test_calculates_daily_ohlc_moves_from_reference_price() -> None:
    daily_bars = (
        make_daily_bar(
            bar_date=date(2026, 4, 17),
            open_price=105.0,
            high_price=110.0,
            low_price=95.0,
            close_price=108.0,
        ),
        make_daily_bar(
            bar_date=date(2026, 4, 20),
            open_price=107.0,
            high_price=112.0,
            low_price=90.0,
            close_price=92.0,
        ),
    )

    moves = DailyMoveAnalyzer().analyze(
        daily_bars=daily_bars,
        reference_price=100.0,
    )

    assert len(moves) == 2

    first_move = moves[0]
    assert first_move.trading_day_index == 1
    assert first_move.date == date(2026, 4, 17)
    assert first_move.open_percent == pytest.approx(5.0)
    assert first_move.high_percent == pytest.approx(10.0)
    assert first_move.low_percent == pytest.approx(-5.0)
    assert first_move.close_percent == pytest.approx(8.0)

    second_move = moves[1]
    assert second_move.trading_day_index == 2
    assert second_move.date == date(2026, 4, 20)
    assert second_move.open_percent == pytest.approx(7.0)
    assert second_move.high_percent == pytest.approx(12.0)
    assert second_move.low_percent == pytest.approx(-10.0)
    assert second_move.close_percent == pytest.approx(-8.0)


def test_trading_day_index_counts_available_bars() -> None:
    daily_bars = (
        make_daily_bar(
            bar_date=date(2026, 4, 17),
            open_price=100.0,
            high_price=101.0,
            low_price=99.0,
            close_price=100.0,
        ),
        make_daily_bar(
            bar_date=date(2026, 4, 20),
            open_price=100.0,
            high_price=101.0,
            low_price=99.0,
            close_price=100.0,
        ),
        make_daily_bar(
            bar_date=date(2026, 4, 21),
            open_price=100.0,
            high_price=101.0,
            low_price=99.0,
            close_price=100.0,
        ),
    )

    moves = DailyMoveAnalyzer().analyze(
        daily_bars=daily_bars,
        reference_price=100.0,
    )

    assert tuple(
        move.trading_day_index
        for move in moves
    ) == (
        1,
        2,
        3,
    )


def test_returns_empty_result_for_empty_price_series() -> None:
    moves = DailyMoveAnalyzer().analyze(
        daily_bars=(),
        reference_price=100.0,
    )

    assert moves == ()


@pytest.mark.parametrize(
    "reference_price",
    (
        0.0,
        -100.0,
    ),
)
def test_rejects_non_positive_reference_price(
    reference_price: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="reference_price must be greater than zero",
    ):
        DailyMoveAnalyzer().analyze(
            daily_bars=(),
            reference_price=reference_price,
        )


def test_rejects_bars_in_descending_date_order() -> None:
    daily_bars = (
        make_daily_bar(
            bar_date=date(2026, 4, 20),
            open_price=100.0,
            high_price=105.0,
            low_price=95.0,
            close_price=102.0,
        ),
        make_daily_bar(
            bar_date=date(2026, 4, 17),
            open_price=100.0,
            high_price=105.0,
            low_price=95.0,
            close_price=102.0,
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "daily_bars must be ordered "
            "by ascending unique date"
        ),
    ):
        DailyMoveAnalyzer().analyze(
            daily_bars=daily_bars,
            reference_price=100.0,
        )


def test_rejects_duplicate_bar_dates() -> None:
    daily_bars = (
        make_daily_bar(
            bar_date=date(2026, 4, 17),
            open_price=100.0,
            high_price=105.0,
            low_price=95.0,
            close_price=102.0,
        ),
        make_daily_bar(
            bar_date=date(2026, 4, 17),
            open_price=102.0,
            high_price=106.0,
            low_price=98.0,
            close_price=104.0,
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "daily_bars must be ordered "
            "by ascending unique date"
        ),
    ):
        DailyMoveAnalyzer().analyze(
            daily_bars=daily_bars,
            reference_price=100.0,
        )