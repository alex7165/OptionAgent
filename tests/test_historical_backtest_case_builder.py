from datetime import date

import pytest

from app.analysis.historical_backtest_case_builder import (
    HistoricalBacktestCaseBuilder,
    HistoricalBacktestCaseSkipReason,
)
from app.marketdata.earnings_api_provider import HistoricalEarningsReaction
from app.marketdata.models import ExpirationChain, OptionQuote
from app.marketdata.price_history_provider import DailyBar


class RecordingPriceProvider:
    def __init__(self, bars: tuple[DailyBar, ...]) -> None:
        self.bars = bars
        self.calls: list[dict[str, object]] = []

    def get_daily_bars(self, symbol, start_date, end_date):
        self.calls.append(
            {
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date,
            }
        )
        return tuple(
            bar for bar in self.bars if start_date <= bar.date <= end_date
        )


class RecordingHistoricalOptionProvider:
    def __init__(self, chain: ExpirationChain | None) -> None:
        self.chain = chain
        self.calls: list[dict[str, object]] = []

    def get_expiration_chain(self, symbol, expiration, as_of_date):
        self.calls.append(
            {
                "symbol": symbol,
                "expiration": expiration,
                "as_of_date": as_of_date,
            }
        )
        return self.chain


def earnings(report_date: date = date(2026, 7, 14)) -> HistoricalEarningsReaction:
    return HistoricalEarningsReaction(
        report_date=report_date,
        symbol="TEST",
        eps_surprise_percent=None,
        eps_yoy_percent=None,
        eps_beat=None,
        revenue_surprise_percent=None,
        revenue_yoy_percent=None,
        revenue_beat=None,
        reactions=(),
    )


def bar(day: date, close: float = 100.0) -> DailyBar:
    return DailyBar(
        date=day,
        open=close,
        high=close + 2,
        low=close - 2,
        close=close,
        volume=1_000_000,
    )


def quote(option_type: str, strike: float, bid: float, ask: float) -> OptionQuote:
    return OptionQuote(
        symbol="TEST",
        expiration=date(2026, 7, 17),
        strike=strike,
        option_type=option_type,
        bid=bid,
        ask=ask,
        volume=100,
        open_interest=1_000,
    )


def valid_chain() -> ExpirationChain:
    return ExpirationChain(
        symbol="TEST",
        expiration=date(2026, 7, 17),
        quotes=[
            quote("call", 100.0, 2.9, 3.1),
            quote("put", 100.0, 2.9, 3.1),
        ],
    )


def test_builds_case_from_actual_pre_earnings_market_data() -> None:
    prices = RecordingPriceProvider(
        (
            bar(date(2026, 7, 10), 98.0),
            bar(date(2026, 7, 13), 100.0),
            bar(date(2026, 7, 14), 104.0),
            bar(date(2026, 7, 15), 103.0),
            bar(date(2026, 7, 17), 102.0),
        )
    )
    options = RecordingHistoricalOptionProvider(valid_chain())
    builder = HistoricalBacktestCaseBuilder(prices, options)

    result = builder.build(earnings())

    assert result.built is True
    assert result.skip_reason is None
    assert result.as_of_date == date(2026, 7, 13)
    assert result.expiration == date(2026, 7, 17)
    assert result.case is not None
    assert result.case.reference_price == 100.0
    assert result.case.expected_move.percent == pytest.approx(0.06)
    assert tuple(item.date for item in result.case.daily_bars) == (
        date(2026, 7, 14),
        date(2026, 7, 15),
        date(2026, 7, 17),
    )
    assert options.calls == [
        {
            "symbol": "TEST",
            "expiration": date(2026, 7, 17),
            "as_of_date": date(2026, 7, 13),
        }
    ]


def test_skips_case_when_historical_option_chain_is_unavailable() -> None:
    prices = RecordingPriceProvider((bar(date(2026, 7, 13)),))
    builder = HistoricalBacktestCaseBuilder(
        prices,
        RecordingHistoricalOptionProvider(None),
    )

    result = builder.build(earnings())

    assert result.built is False
    assert result.case is None
    assert result.skip_reason is (
        HistoricalBacktestCaseSkipReason.HISTORICAL_OPTION_CHAIN_UNAVAILABLE
    )


def test_skips_case_instead_of_inventing_expected_move() -> None:
    prices = RecordingPriceProvider((bar(date(2026, 7, 13)),))
    empty_chain = ExpirationChain(
        symbol="TEST",
        expiration=date(2026, 7, 17),
        quotes=[],
    )
    builder = HistoricalBacktestCaseBuilder(
        prices,
        RecordingHistoricalOptionProvider(empty_chain),
    )

    result = builder.build(earnings())

    assert result.built is False
    assert result.skip_reason is (
        HistoricalBacktestCaseSkipReason.EXPECTED_MOVE_UNAVAILABLE
    )


def test_skips_case_when_reference_price_is_unavailable() -> None:
    prices = RecordingPriceProvider((bar(date(2026, 7, 14)),))
    options = RecordingHistoricalOptionProvider(valid_chain())
    builder = HistoricalBacktestCaseBuilder(prices, options)

    result = builder.build(earnings())

    assert result.built is False
    assert result.skip_reason is (
        HistoricalBacktestCaseSkipReason.REFERENCE_PRICE_UNAVAILABLE
    )
    assert options.calls == []


def test_skips_case_when_post_earnings_bars_are_unavailable() -> None:
    prices = RecordingPriceProvider((bar(date(2026, 7, 13)),))
    builder = HistoricalBacktestCaseBuilder(
        prices,
        RecordingHistoricalOptionProvider(valid_chain()),
    )

    result = builder.build(earnings())

    assert result.built is False
    assert result.skip_reason is (
        HistoricalBacktestCaseSkipReason.OUTCOME_PRICE_HISTORY_UNAVAILABLE
    )


def test_build_many_orders_results_chronologically() -> None:
    prices = RecordingPriceProvider((bar(date(2026, 7, 9)),))
    builder = HistoricalBacktestCaseBuilder(
        prices,
        RecordingHistoricalOptionProvider(None),
    )

    results = builder.build_many(
        (
            earnings(date(2026, 7, 14)),
            earnings(date(2026, 7, 10)),
        )
    )

    assert tuple(item.earnings.report_date for item in results) == (
        date(2026, 7, 10),
        date(2026, 7, 14),
    )


def test_rejects_invalid_reference_lookback() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        HistoricalBacktestCaseBuilder(
            RecordingPriceProvider(()),
            RecordingHistoricalOptionProvider(None),
            reference_lookback_days=0,
        )
