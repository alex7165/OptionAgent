from datetime import date
from pathlib import Path

from app.marketdata.models import EarningsEvent, MarketSnapshot, Quote
from app.run_earnings_test import build_events, candidate_status, run_batch


class DummyCandidate:
    def __init__(self, symbol, failed_rules=None, strike_selection=None):
        self.earnings_event = EarningsEvent(
            symbol=symbol,
            report_date=date(2026, 7, 14),
        )
        self.failed_rules = failed_rules or []
        self.strike_selection = strike_selection
        self.snapshot = MarketSnapshot(
            symbol=symbol,
            quote=Quote(symbol, 100.0, "USD", "test"),
        )


class DummyAnalyzer:
    def __init__(self):
        self.events = None

    def create_candidates(self, events):
        self.events = events
        return [DummyCandidate(event.symbol, ["missing_expiration_chain"]) for event in events]


class DummyFactory:
    def __init__(self, analyzer):
        self.analyzer = analyzer
        self.market_data = None

    def create(self, market_data):
        self.market_data = market_data
        return self.analyzer


class DummyMarketData:
    pass


def test_build_events_uses_manual_symbols_and_report_date():
    report_date = date(2026, 7, 14)

    events = build_events(["c", " GS "], report_date)

    assert [event.symbol for event in events] == ["C", "GS"]
    assert all(event.report_date == report_date for event in events)
    assert all(event.timing == "before market open" for event in events)


def test_candidate_status_reports_failed_rules():
    candidate = DummyCandidate(
        "C",
        failed_rules=["missing_expiration_chain", "missing_expected_move"],
    )

    status, reason = candidate_status(candidate)

    assert status == "AUSGESCHLOSSEN"
    assert reason == "missing_expiration_chain, missing_expected_move"


def test_run_batch_uses_factory_and_writes_excel(tmp_path, capsys):
    analyzer = DummyAnalyzer()
    factory = DummyFactory(analyzer)
    market_data = DummyMarketData()
    output_path = tmp_path / "earnings_test.xlsx"

    candidates = run_batch(
        symbols=["C", "JPM"],
        report_date=date(2026, 7, 14),
        output_path=output_path,
        market_data=market_data,
        analyzer_factory=factory,
    )

    assert factory.market_data is market_data
    assert [event.symbol for event in analyzer.events] == ["C", "JPM"]
    assert len(candidates) == 2
    assert output_path.exists()

    output = capsys.readouterr().out
    assert "C" in output
    assert "JPM" in output
    assert "missing_expiration_chain" in output
