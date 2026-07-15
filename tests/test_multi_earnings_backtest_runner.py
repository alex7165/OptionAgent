from datetime import date

import pytest

from app.analysis.multi_earnings_backtest_runner import (
    EarningsBacktestCase,
    MultiEarningsBacktestRunner,
)
from app.analysis.strategy import Strategy
from app.analysis.strategy_selector import StrikeSelectionSource
from app.analysis.strike_selection import StrikeSelection
from app.marketdata.models import OptionQuote
from app.marketdata.price_history_provider import DailyBar


def quote(option_type: str, strike: float) -> OptionQuote:
    return OptionQuote(
        symbol="TEST",
        expiration=date(2026, 7, 17),
        strike=strike,
        option_type=option_type,
        bid=1.0,
        ask=1.1,
        last=1.05,
        volume=100,
        open_interest=500,
    )


def selection() -> StrikeSelection:
    return StrikeSelection(
        put=quote("put", 95.0),
        call=quote("call", 105.0),
        put_target=95.0,
        call_target=105.0,
        strategy=Strategy.SHORT_STRANGLE,
    )


def bar(day: int, high: float, low: float, close: float) -> DailyBar:
    return DailyBar(
        date=date(2026, 7, day),
        open=100.0,
        high=high,
        low=low,
        close=close,
        volume=1_000_000,
    )


def case(
    report_day: int,
    source: StrikeSelectionSource,
    bars: tuple[DailyBar, ...],
    exit_day: int = 2,
) -> EarningsBacktestCase:
    return EarningsBacktestCase(
        report_date=date(2026, 7, report_day),
        selection=selection(),
        daily_bars=bars,
        reference_price=100.0,
        exit_trading_day_index=exit_day,
        selection_source=source,
    )


def test_aggregates_multiple_earnings_and_orders_results() -> None:
    summary = MultiEarningsBacktestRunner().run(
        symbol=" nvda ",
        cases=(
            case(
                20,
                StrikeSelectionSource.HISTORICAL,
                (
                    bar(21, 104.0, 96.0, 102.0),
                    bar(22, 106.0, 97.0, 104.0),
                ),
            ),
            case(
                10,
                StrikeSelectionSource.EXPECTED_MOVE,
                (
                    bar(11, 103.0, 94.0, 97.0),
                    bar(12, 104.0, 93.0, 94.0),
                ),
            ),
        ),
    )

    assert summary.symbol == "NVDA"
    assert tuple(result.report_date.day for result in summary.results) == (10, 20)
    assert summary.overall.observation_count == 2
    assert summary.overall.inside_rate == pytest.approx(0.5)
    assert summary.overall.put_touch_rate == pytest.approx(0.5)
    assert summary.overall.call_touch_rate == pytest.approx(0.5)
    assert summary.overall.put_finish_outside_rate == pytest.approx(0.5)
    assert summary.overall.call_finish_outside_rate == pytest.approx(0.0)
    assert summary.overall.average_max_adverse_move_percent == pytest.approx(-5.5)
    assert summary.overall.average_max_favorable_move_percent == pytest.approx(5.0)
    assert summary.overall.average_holding_days == pytest.approx(2.0)


def test_groups_metrics_by_selection_source() -> None:
    summary = MultiEarningsBacktestRunner().run(
        symbol="TEST",
        cases=(
            case(
                10,
                StrikeSelectionSource.HISTORICAL,
                (
                    bar(11, 103.0, 97.0, 101.0),
                    bar(12, 104.0, 96.0, 102.0),
                ),
            ),
            case(
                20,
                StrikeSelectionSource.HISTORICAL,
                (
                    bar(21, 106.0, 98.0, 106.0),
                    bar(22, 108.0, 99.0, 107.0),
                ),
            ),
            case(
                25,
                StrikeSelectionSource.EXPECTED_MOVE,
                (
                    bar(26, 102.0, 98.0, 100.0),
                    bar(27, 103.0, 97.0, 101.0),
                ),
            ),
        ),
    )

    grouped = {
        item.selection_source: item.metrics
        for item in summary.by_selection_source
    }

    assert grouped[StrikeSelectionSource.HISTORICAL].observation_count == 2
    assert grouped[StrikeSelectionSource.HISTORICAL].inside_rate == pytest.approx(0.5)
    assert grouped[StrikeSelectionSource.HISTORICAL].call_touch_rate == pytest.approx(0.5)
    assert grouped[StrikeSelectionSource.EXPECTED_MOVE].observation_count == 1
    assert grouped[StrikeSelectionSource.EXPECTED_MOVE].inside_rate == pytest.approx(1.0)


def test_uses_each_cases_selected_exit_day() -> None:
    summary = MultiEarningsBacktestRunner().run(
        symbol="TEST",
        cases=(
            case(
                10,
                StrikeSelectionSource.HISTORICAL,
                (
                    bar(11, 103.0, 97.0, 101.0),
                    bar(12, 120.0, 80.0, 110.0),
                ),
                exit_day=1,
            ),
            case(
                20,
                StrikeSelectionSource.HISTORICAL,
                (
                    bar(21, 103.0, 97.0, 101.0),
                    bar(22, 104.0, 96.0, 102.0),
                ),
                exit_day=2,
            ),
        ),
    )

    assert summary.results[0].outcome.call_touched is False
    assert summary.overall.average_holding_days == pytest.approx(1.5)


def test_rejects_empty_cases() -> None:
    with pytest.raises(ValueError, match="cases must not be empty"):
        MultiEarningsBacktestRunner().run("TEST", ())


def test_rejects_duplicate_report_dates() -> None:
    duplicate = case(
        10,
        StrikeSelectionSource.HISTORICAL,
        (bar(11, 103.0, 97.0, 101.0),),
        exit_day=1,
    )

    with pytest.raises(ValueError, match="unique report dates"):
        MultiEarningsBacktestRunner().run("TEST", (duplicate, duplicate))


def test_rejects_empty_symbol() -> None:
    valid_case = case(
        10,
        StrikeSelectionSource.HISTORICAL,
        (bar(11, 103.0, 97.0, 101.0),),
        exit_day=1,
    )

    with pytest.raises(ValueError, match="symbol must not be empty"):
        MultiEarningsBacktestRunner().run(" ", (valid_case,))
