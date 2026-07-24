import json

import pytest
from datetime import date

from openpyxl import Workbook

from app.analysis.pending_training_cohort import (
    PendingTradeExcelImporter,
    PendingTrainingCohortBuilder,
    PendingTrainingCohortRepository,
)
from app.marketdata.price_history_provider import DailyBar, PriceHistoryProvider


class FakePriceHistoryProvider(PriceHistoryProvider):
    def __init__(self, bars_by_symbol):
        self.bars_by_symbol = bars_by_symbol
        self.calls = []

    def get_daily_bars(self, symbol, start_date, end_date):
        self.calls.append((symbol, start_date, end_date))
        return self.bars_by_symbol.get(symbol, ())


def write_trade_file(path):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Earnings Crush"
    sheet.append(
        [
            "Aktie", "Kurs", "Strategie", "Score",
            "ShortPutProzent", "LongPutProzent",
            "ShortCallProzent", "LongCallProzent",
            "ShortPutStrike", "LongPutStrike",
            "ShortCallStrike", "LongCallStrike",
        ]
    )
    sheet.append(
        ["XYZ", 100.0, "Short Strangle", 48, -10, None, 10, None,
         90.0, None, 110.0, None]
    )
    workbook.save(path)


def test_imports_daily_trade_excel_and_derives_friday_expiration(tmp_path):
    path = tmp_path / "daily_trades_2026-07-20.xlsx"
    write_trade_file(path)

    entries = PendingTradeExcelImporter().load(path, date(2026, 7, 20))

    assert len(entries) == 1
    assert entries[0].symbol == "XYZ"
    assert entries[0].expiration == date(2026, 7, 24)
    assert entries[0].short_put_strike == 90.0
    assert entries[0].long_put_strike is None


def test_captures_first_completed_trading_day_after_decision_date():
    provider = FakePriceHistoryProvider(
        {
            "XYZ": (
                DailyBar(date(2026, 7, 21), 105, 112, 98, 108, 5000),
                DailyBar(date(2026, 7, 22), 107, 109, 103, 104, 4000),
            )
        }
    )
    from app.analysis.pending_training_cohort import PendingTradeEntry
    from app.analysis.strategy import Strategy

    cohort = PendingTrainingCohortBuilder(provider).build(
        (
            PendingTradeEntry(
                symbol="xyz",
                decision_date=date(2026, 7, 20),
                expiration=date(2026, 7, 24),
                reference_price=100,
                strategy=Strategy.SHORT_STRANGLE,
                score=48,
                short_put_strike=90,
                short_call_strike=110,
            ),
        ),
        source_file="trades.xlsx",
    )

    snapshot = cohort.captured_trades[0]
    assert snapshot.reaction_date == date(2026, 7, 21)
    assert snapshot.gap_percent == pytest.approx(5.0)
    assert snapshot.close_move_percent == pytest.approx(8.0)
    assert snapshot.call_touched is True
    assert snapshot.put_touched is False
    assert snapshot.finished_inside_short_strikes is True
    assert provider.calls == [
        ("XYZ", date(2026, 7, 21), date(2026, 7, 27))
    ]


def test_records_missing_symbol_without_using_current_wall_clock():
    from app.analysis.pending_training_cohort import PendingTradeEntry
    from app.analysis.strategy import Strategy

    cohort = PendingTrainingCohortBuilder(
        FakePriceHistoryProvider({})
    ).build(
        (
            PendingTradeEntry(
                symbol="NOPE",
                decision_date=date(2026, 7, 20),
                expiration=date(2026, 7, 24),
                reference_price=100,
                strategy=Strategy.SHORT_STRANGLE,
                score=None,
                short_put_strike=90,
                short_call_strike=110,
            ),
        ),
        source_file="trades.xlsx",
    )

    assert cohort.captured_trades == ()
    assert cohort.missing_symbols == ("NOPE",)


def test_repository_serializes_dates_and_strategy(tmp_path):
    from app.analysis.pending_training_cohort import (
        FirstReactionSnapshot,
        PendingTrainingCohort,
    )
    from app.analysis.strategy import Strategy

    cohort = PendingTrainingCohort(
        decision_date=date(2026, 7, 20),
        source_file="trades.xlsx",
        captured_trades=(
            FirstReactionSnapshot(
                symbol="XYZ",
                decision_date=date(2026, 7, 20),
                expiration=date(2026, 7, 24),
                reference_price=100,
                strategy=Strategy.SHORT_STRANGLE,
                score=48,
                short_put_strike=90,
                short_call_strike=110,
                long_put_strike=None,
                long_call_strike=None,
                reaction_date=date(2026, 7, 21),
                open=105,
                high=112,
                low=98,
                close=108,
                volume=5000,
                gap_percent=5,
                close_move_percent=8,
                high_move_percent=12,
                low_move_percent=-2,
                put_touched=False,
                call_touched=True,
                finished_inside_short_strikes=True,
            ),
        ),
    )
    path = tmp_path / "pending.json"

    PendingTrainingCohortRepository().save(cohort, path)
    payload = json.loads(path.read_text())

    assert payload["decision_date"] == "2026-07-20"
    assert payload["captured_trades"][0]["reaction_date"] == "2026-07-21"
    assert payload["captured_trades"][0]["strategy"] == "Short Strangle"
