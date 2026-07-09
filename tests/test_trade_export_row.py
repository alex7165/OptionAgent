from app.analysis.trade_export_row import TradeExportRow


def test_trade_export_row_can_be_created():
    row = TradeExportRow(
        aktie="NVDA",
        kurs=200.0,
        strategie="Short Strangle",
        short_put_prozent=-5.0,
        short_call_prozent=5.0,
        short_put_strike=190.0,
        short_call_strike=210.0,
    )

    assert row.aktie == "NVDA"
    assert row.strategie == "Short Strangle"
    assert row.short_put_strike == 190.0