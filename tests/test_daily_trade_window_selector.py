from datetime import date

from app.analysis.daily_trade_window_selector import DailyTradeWindowSelector
from app.marketdata.models import EarningsEvent


def event(symbol: str, day: date, timing: str) -> EarningsEvent:
    return EarningsEvent(symbol=symbol, report_date=day, timing=timing)


def test_selects_today_amc_and_next_weekday_bmo() -> None:
    selector = DailyTradeWindowSelector()
    today = date(2026, 7, 15)
    events = [
        event("AMC", today, "after market close"),
        event("TODAY_BMO", today, "before market open"),
        event("BMO", date(2026, 7, 16), "BMO"),
        event("NEXT_AMC", date(2026, 7, 16), "after market close"),
    ]

    result = selector.select(events, today)

    assert [item.symbol for item in result.events] == ["AMC", "BMO"]
    assert result.next_trading_date == date(2026, 7, 16)


def test_friday_uses_monday_as_next_trading_weekday() -> None:
    selector = DailyTradeWindowSelector()
    friday = date(2026, 7, 17)
    monday = date(2026, 7, 20)

    result = selector.select(
        [event("MON", monday, "before market open")],
        friday,
    )

    assert result.next_trading_date == monday
    assert [item.symbol for item in result.events] == ["MON"]
