from datetime import date

from app.analysis.entry_decision_snapshot import EntryDecisionSnapshot
from app.analysis.strategy import Strategy
from app.analysis.trade_management_chart_context import TradeManagementChartContextAnalyzer
from app.marketdata.price_history_provider import DailyBar, PriceHistoryProvider


class StubProvider(PriceHistoryProvider):
    def __init__(self, bars):
        self.bars = tuple(bars)

    def get_daily_bars(self, symbol, start_date, end_date):
        return tuple(bar for bar in self.bars if start_date <= bar.date <= end_date)


def _entry():
    return EntryDecisionSnapshot(
        symbol="GS",
        decision_date=date(2026, 7, 13),
        report_date=date(2026, 7, 14),
        expiration=date(2026, 7, 17),
        strategy=Strategy.SHORT_STRANGLE,
        reference_price=100.0,
        short_put_strike=90.0,
        short_call_strike=105.0,
    )


def test_chart_context_uses_real_report_date_and_as_of_cutoff():
    bars = [
        DailyBar(date(2026, 7, 13), 99, 101, 98, 100, 1000),
        DailyBar(date(2026, 7, 14), 108, 112, 107, 111, 3000),
        DailyBar(date(2026, 7, 15), 111, 114, 110, 113, 2500),
        DailyBar(date(2026, 7, 16), 113, 120, 112, 119, 4000),
    ]
    result = TradeManagementChartContextAnalyzer(StubProvider(bars)).analyze(
        _entry(), date(2026, 7, 15)
    )
    assert result.as_of_trading_date == date(2026, 7, 15)
    assert result.current_close == 113
    assert round(result.gap_from_pre_earnings_close_percent, 6) == 8.0
    assert result.gap_held is True


def test_chart_context_rejects_date_before_actual_earnings():
    analyzer = TradeManagementChartContextAnalyzer(StubProvider(()))
    try:
        analyzer.analyze(_entry(), date(2026, 7, 13))
    except ValueError as exc:
        assert "before report_date" in str(exc)
    else:
        raise AssertionError("ValueError expected")
