from datetime import date

from openpyxl import Workbook

from app.analysis.trade_excel_snapshot_loader import TradeExcelSnapshotLoader
from app.marketdata.models import EarningsEvent


class DummyCalendarProvider:
    def get_events(self, start_date, end_date):
        return [
            EarningsEvent(
                symbol="TEST",
                report_date=date(2026, 7, 22),
                timing="after market close",
            )
        ]


def test_loads_trade_snapshot_from_excel(tmp_path):
    path = tmp_path / "daily_trades_2026-07-22.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(
        [
            "Aktie",
            "Kurs",
            "Strategie",
            "ShortPutStrike",
            "ShortCallStrike",
        ]
    )
    sheet.append(["TEST", 100, "Short Strangle", 95, 105])
    workbook.save(path)

    result = TradeExcelSnapshotLoader(DummyCalendarProvider()).load((path,))

    assert len(result) == 1
    assert result[0].symbol == "TEST"
    assert result[0].decision_date == date(2026, 7, 22)
    assert result[0].report_date == date(2026, 7, 22)
    assert result[0].expiration == date(2026, 7, 24)
    assert result[0].short_put_strike == 95
    assert result[0].short_call_strike == 105


def test_skips_empty_excel(tmp_path):
    path = tmp_path / "daily_trades_2026-07-23.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(
        [
            "Aktie",
            "Kurs",
            "Strategie",
            "ShortPutStrike",
            "ShortCallStrike",
        ]
    )
    workbook.save(path)

    result = TradeExcelSnapshotLoader(DummyCalendarProvider()).load((path,))

    assert result == ()
