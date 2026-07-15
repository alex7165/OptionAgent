from datetime import date
from pathlib import Path

from app.marketdata.models import EarningsEvent
from app.run_daily_trades import run_daily


class CalendarProvider:
    def get_events(self, start_date, end_date):
        return [
            EarningsEvent("ZZZ", start_date, "after market close"),
            EarningsEvent("AAA", end_date, "before market open"),
            EarningsEvent("SKIP", start_date, "before market open"),
        ]


class Analyzer:
    def __init__(self):
        self.events = None

    def create_candidates(self, events):
        self.events = events
        return []


class Factory:
    def __init__(self, analyzer):
        self.analyzer = analyzer

    def create(self, market_data):
        return self.analyzer


def test_run_daily_uses_only_correct_trade_window(tmp_path, monkeypatch) -> None:
    analyzer = Analyzer()
    monkeypatch.setattr(
        "app.run_daily_trades.TradeExporter.export_excel",
        lambda self, candidates, output_path: None,
    )

    result = run_daily(
        trade_date=date(2026, 7, 15),
        output_path=Path(tmp_path) / "daily.xlsx",
        calendar_provider=CalendarProvider(),
        market_data=object(),
        analyzer_factory=Factory(analyzer),
    )

    assert result == []
    assert [event.symbol for event in analyzer.events] == ["AAA", "ZZZ"]
