import pytest

from datetime import date

from app.analysis.earnings_crush_candidate import EarningsCrushCandidate
from app.analysis.strike_selection import StrikeSelection
from app.analysis.trade_exporter import TradeExporter
from app.marketdata.models import EarningsEvent, MarketSnapshot, OptionQuote, Quote
from openpyxl import load_workbook


def test_export_excel_creates_file(tmp_path):
    candidate = EarningsCrushCandidate(
        earnings_event=EarningsEvent(
            symbol="NVDA",
            report_date=date(2026, 8, 26),
            timing="AMC",
            source="test",
        ),
        snapshot=MarketSnapshot(
            symbol="NVDA",
            quote=Quote(
                symbol="NVDA",
                price=200,
                currency="USD",
                source="test",
            ),
            news=[],
        ),
    )

    candidate.strike_selection = StrikeSelection(
        put=OptionQuote(
            symbol="NVDA",
            expiration=date(2026, 8, 28),
            strike=180,
            option_type="put",
        ),
        call=OptionQuote(
            symbol="NVDA",
            expiration=date(2026, 8, 28),
            strike=220,
            option_type="call",
        ),
        put_target=180,
        call_target=220,
    )

    output = tmp_path / "earnings.xlsx"

    TradeExporter().export_excel([candidate], output)

    assert output.exists()

def test_export_excel_writes_headers_and_values(tmp_path):
    candidate = EarningsCrushCandidate(
        earnings_event=EarningsEvent(
            symbol="NVDA",
            report_date=date(2026, 8, 26),
            timing="AMC",
            source="test",
        ),
        snapshot=MarketSnapshot(
            symbol="NVDA",
            quote=Quote(
                symbol="NVDA",
                price=200,
                currency="USD",
                source="test",
            ),
            news=[],
        ),
    )

    candidate.strike_selection = StrikeSelection(
        put=OptionQuote(
            symbol="NVDA",
            expiration=date(2026, 8, 28),
            strike=180,
            option_type="put",
        ),
        call=OptionQuote(
            symbol="NVDA",
            expiration=date(2026, 8, 28),
            strike=220,
            option_type="call",
        ),
        put_target=180,
        call_target=220,
    )

    output = tmp_path / "earnings.xlsx"

    TradeExporter().export_excel([candidate], output)

    workbook = load_workbook(output)
    worksheet = workbook.active

    assert worksheet["A1"].value == "Aktie"
    assert worksheet["B1"].value == "Kurs"
    assert worksheet["C1"].value == "Strategie"

    assert worksheet["A2"].value == "NVDA"
    assert worksheet["B2"].value == 200
    assert worksheet["C2"].value == "Short Strangle"
    assert worksheet["D2"].value == pytest.approx(-10)
    assert worksheet["F2"].value == pytest.approx(10)
    assert worksheet["H2"].value == 180
    assert worksheet["J2"].value == 220