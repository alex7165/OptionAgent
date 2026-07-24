from datetime import date
from pathlib import Path

from app.marketdata.models import EarningsEvent
from app.run_daily_trades import run_daily


class CalendarProvider:
    def __init__(self):
        self.requested_range = None

    def get_events(self, start_date, end_date):
        self.requested_range = (start_date, end_date)
        next_date = date(2026, 7, 16)
        return [
            EarningsEvent("ZZZ", start_date, "post-market"),
            EarningsEvent("AAA", next_date, "pre-market"),
            EarningsEvent("SKIP", start_date, "before market open"),
        ]


class Analyzer:
    def __init__(self):
        self.events = []

    def create_candidates(self, events):
        self.events.extend(events)
        return []


class Factory:
    def __init__(self, analyzer):
        self.analyzer = analyzer

    def create(self, market_data):
        return self.analyzer


def test_run_daily_uses_only_correct_trade_window(tmp_path, monkeypatch) -> None:
    analyzer = Analyzer()
    provider = CalendarProvider()
    monkeypatch.setattr(
        "app.run_daily_trades.TradeExporter.export_excel",
        lambda self, candidates, output_path: None,
    )

    result = run_daily(
        trade_date=date(2026, 7, 15),
        output_path=Path(tmp_path) / "daily.xlsx",
        calendar_provider=provider,
        market_data=object(),
        analyzer_factory=Factory(analyzer),
    )

    assert result == []
    assert provider.requested_range == (
        date(2026, 7, 15),
        date(2026, 7, 17),
    )
    assert [event.symbol for event in analyzer.events] == ["AAA", "ZZZ"]


class Candidate:
    def __init__(self, symbol):
        self.symbol = symbol


class FailingSingleSymbolAnalyzer:
    def __init__(self):
        self.seen_symbols = []

    def create_candidates(self, events):
        event = events[0]
        self.seen_symbols.append(event.symbol)
        if event.symbol == "AAA":
            raise RuntimeError("option data failed")
        return [Candidate(event.symbol)]


def test_run_daily_continues_after_single_symbol_error(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    analyzer = FailingSingleSymbolAnalyzer()
    exported = {}

    def capture_export(self, candidates, output_path):
        exported["symbols"] = [candidate.symbol for candidate in candidates]

    monkeypatch.setattr(
        "app.run_daily_trades.TradeExporter.export_excel",
        capture_export,
    )
    monkeypatch.setattr(
        "app.run_daily_trades.format_candidate",
        lambda candidate: candidate.symbol,
    )
    monkeypatch.setattr(
        "app.run_daily_trades.format_selection_details",
        lambda candidate: [],
    )

    result = run_daily(
        trade_date=date(2026, 7, 15),
        output_path=Path(tmp_path) / "daily.xlsx",
        calendar_provider=CalendarProvider(),
        market_data=object(),
        analyzer_factory=Factory(analyzer),
    )

    assert analyzer.seen_symbols == ["AAA", "ZZZ"]
    assert [candidate.symbol for candidate in result] == ["ZZZ"]
    assert exported["symbols"] == ["ZZZ"]

    output = capsys.readouterr().out
    assert "AAA    TECHNISCHER FEHLER" in output
    assert "RuntimeError: option data failed" in output
    assert "Technische Fehler: 1" in output


def test_technical_404_is_reported_as_missing_option_chain() -> None:
    from app.run_daily_trades import _technical_error_reason

    class Response:
        status_code = 404

    error = RuntimeError("not found")
    error.response = Response()

    assert _technical_error_reason(error) == "option_chain_not_available"


def test_run_daily_loads_dotenv_before_creating_analyzer(
    tmp_path,
    monkeypatch,
) -> None:
    calls = []
    analyzer = Analyzer()

    monkeypatch.setattr(
        "app.run_daily_trades.load_dotenv",
        lambda: calls.append("dotenv"),
    )
    monkeypatch.setattr(
        "app.run_daily_trades.TradeExporter.export_excel",
        lambda self, candidates, output_path: None,
    )

    class RecordingFactory(Factory):
        def create(self, market_data):
            calls.append("factory")
            return super().create(market_data)

    run_daily(
        trade_date=date(2026, 7, 15),
        output_path=Path(tmp_path) / "daily.xlsx",
        calendar_provider=CalendarProvider(),
        market_data=object(),
        analyzer_factory=RecordingFactory(analyzer),
    )

    assert calls == ["dotenv", "factory"]


def test_run_daily_reports_historical_selection_status(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    analyzer = Analyzer()
    analyzer.historical_inputs_loader = object()

    monkeypatch.setattr(
        "app.run_daily_trades.TradeExporter.export_excel",
        lambda self, candidates, output_path: None,
    )

    run_daily(
        trade_date=date(2026, 7, 15),
        output_path=Path(tmp_path) / "daily.xlsx",
        calendar_provider=CalendarProvider(),
        market_data=object(),
        analyzer_factory=Factory(analyzer),
    )

    assert "Historische Auswahl: aktiv" in capsys.readouterr().out
