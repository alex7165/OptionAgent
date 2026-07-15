from app.marketdata.models import EarningsEvent
from datetime import date
from app.analysis.earnings_crush_candidate import EarningsCrushCandidate
from app.analysis.expected_move import ExpectedMove
from app.analysis.strike_selection import StrikeSelection
from app.analysis.trade_exporter import TradeExporter
from app.marketdata.models import EarningsEvent, MarketSnapshot, OptionQuote, Quote


def test_trade_exporter_exports_short_strangle():
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

    candidate.expected_move = ExpectedMove(
        percent=0.05,
        up_price=210,
        down_price=190,
    )

    candidate.strike_selection = StrikeSelection(
        put=OptionQuote(
            symbol="NVDA",
            expiration=date(2026, 8, 28),
            strike=190,
            option_type="put",
        ),
        call=OptionQuote(
            symbol="NVDA",
            expiration=date(2026, 8, 28),
            strike=210,
            option_type="call",
        ),
        put_target=190,
        call_target=210,
    )

    rows = TradeExporter().export_rows([candidate])

    assert len(rows) == 1
    assert rows[0].aktie == "NVDA"
    assert rows[0].short_put_strike == 190
    assert rows[0].short_call_strike == 210

def test_trade_exporter_includes_score_without_changing_symbol_order():
    candidate = EarningsCrushCandidate(
        earnings_event=EarningsEvent(
            symbol="GS",
            report_date=date(2026, 8, 26),
            timing="AMC",
            source="test",
        ),
        snapshot=MarketSnapshot(
            symbol="GS",
            quote=Quote("GS", 100, "USD", "test"),
            news=[],
        ),
    )
    candidate.strike_selection = StrikeSelection(
        put=OptionQuote(
            symbol="GS",
            expiration=date(2026, 8, 28),
            strike=90,
            option_type="put",
        ),
        call=OptionQuote(
            symbol="GS",
            expiration=date(2026, 8, 28),
            strike=110,
            option_type="call",
        ),
        put_target=90,
        call_target=110,
    )

    class Score:
        total = 87

    class Report:
        trade_score = Score()

    candidate.decision_report = Report()

    rows = TradeExporter().export_rows([candidate])

    assert rows[0].score == 87
