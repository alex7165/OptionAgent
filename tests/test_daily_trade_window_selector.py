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


def test_accepts_common_pre_and_post_market_variants() -> None:
    selector = DailyTradeWindowSelector()
    today = date(2026, 7, 15)
    tomorrow = date(2026, 7, 16)

    result = selector.select(
        [
            event("POST", today, "Post-Market"),
            event("HOURS", today, "After Hours"),
            event("PRE", tomorrow, "Pre-Market"),
        ],
        today,
    )

    assert [item.symbol for item in result.events] == ["HOURS", "POST", "PRE"]


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


def test_selects_numeric_market_times() -> None:
    selector = DailyTradeWindowSelector()
    today = date(2026, 7, 15)
    tomorrow = date(2026, 7, 16)

    result = selector.select(
        [
            event("TODAY_1600", today, "16:00:00"),
            event("TODAY_1615", today, "16:15:00"),
            event("TODAY_0900", today, "09:00:00"),
            event("NEXT_0830", tomorrow, "08:30:00"),
            event("NEXT_0900", tomorrow, "09:00:00"),
            event("NEXT_1600", tomorrow, "16:00:00"),
        ],
        today,
    )

    assert [item.symbol for item in result.events] == [
        "NEXT_0830",
        "NEXT_0900",
        "TODAY_1600",
        "TODAY_1615",
    ]


def test_does_not_classify_regular_market_times_as_bmo_or_amc() -> None:
    selector = DailyTradeWindowSelector()
    today = date(2026, 7, 15)
    tomorrow = date(2026, 7, 16)

    result = selector.select(
        [
            event("TODAY_MIDDAY", today, "12:00:00"),
            event("NEXT_OPEN", tomorrow, "09:30:00"),
            event("NEXT_MIDDAY", tomorrow, "12:00:00"),
        ],
        today,
    )

    assert result.events == ()
