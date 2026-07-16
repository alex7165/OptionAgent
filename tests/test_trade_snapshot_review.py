from datetime import date

from app.analysis.trade_snapshot_review import (
    TradeSnapshot,
    TradeSnapshotReviewRunner,
)
from app.marketdata.price_history_provider import DailyBar, PriceHistoryProvider


class DummyProvider(PriceHistoryProvider):
    def get_daily_bars(self, symbol, start_date, end_date):
        return (
            DailyBar(date(2026, 7, 14), 100, 106, 96, 103, 1000),
            DailyBar(date(2026, 7, 15), 103, 111, 101, 108, 1200),
        )


def test_reviews_every_available_exit_and_repair():
    snapshot = TradeSnapshot(
        symbol="TEST",
        decision_date=date(2026, 7, 13),
        report_date=date(2026, 7, 14),
        reference_price=100,
        short_put_strike=95,
        short_call_strike=105,
    )
    runner = TradeSnapshotReviewRunner(DummyProvider())

    reviews = runner.run((snapshot,), end_date=date(2026, 7, 15))

    assert len(reviews) == 1
    assert len(reviews[0].outcomes) == 2
    assert reviews[0].outcomes[0].call_touched is True
    assert reviews[0].outcomes[1].call_finished_outside is True
    assert reviews[0].repair.triggered is True


def test_skips_snapshot_without_price_bars():
    class EmptyProvider(PriceHistoryProvider):
        def get_daily_bars(self, symbol, start_date, end_date):
            return ()

    snapshot = TradeSnapshot(
        "TEST", date(2026, 7, 13), date(2026, 7, 14), 100, 95, 105
    )

    result = TradeSnapshotReviewRunner(EmptyProvider()).run(
        (snapshot,), end_date=date(2026, 7, 15)
    )

    assert result == ()
