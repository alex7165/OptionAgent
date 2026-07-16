from datetime import date

from app.analysis.entry_decision_snapshot import EntryDecisionSnapshot
from app.analysis.historical_trade_management_context_loader import (
    HistoricalTradeManagementContextLoader,
)
from app.analysis.strategy import Strategy
from app.marketdata.price_history_provider import DailyBar


class EarningsDates:
    def get_report_dates(self, symbol):
        return (date(2025, 7, 15), date(2024, 7, 15))


class Prices:
    def get_daily_bars(self, symbol, start_date, end_date):
        year = end_date.year
        return (
            DailyBar(date(year, 7, 14), 100, 100, 100, 100, 1),
            DailyBar(date(year, 7, 15), 106, 108, 105, 107, 1),
            DailyBar(date(year, 7, 16), 108, 110, 107, 109, 1),
            DailyBar(date(year, 7, 17), 104, 105, 103, 104, 1),
        )


def test_builds_context_from_prior_comparable_earnings():
    entry = EntryDecisionSnapshot(
        "GS",
        date(2026, 7, 13),
        date(2026, 7, 14),
        date(2026, 7, 17),
        Strategy.SHORT_STRANGLE,
        100,
        90,
        105,
    )
    result = HistoricalTradeManagementContextLoader(
        EarningsDates(),
        Prices(),
        minimum_observations=2,
    ).load(entry, date(2026, 7, 15), 109)

    assert result.observation_count == 2
    assert result.probability_finish_back_inside == 1.0
    assert result.probability_continue_higher == 0.0
    assert result.average_remaining_move_percent < 0


def test_ignores_current_and_future_earnings_dates():
    class Dates:
        def get_report_dates(self, symbol):
            return (date(2026, 7, 14), date(2027, 1, 1))

    entry = EntryDecisionSnapshot(
        "GS",
        date(2026, 7, 13),
        date(2026, 7, 14),
        date(2026, 7, 17),
        Strategy.SHORT_STRANGLE,
        100,
        90,
        105,
    )
    result = HistoricalTradeManagementContextLoader(
        Dates(), Prices(), minimum_observations=1
    ).load(entry, date(2026, 7, 15), 109)

    assert result.observation_count == 0
    assert result.probability_finish_back_inside is None



def test_context_reports_comparable_cases_and_total_usable_history():
    entry = EntryDecisionSnapshot(
        "GS",
        date(2026, 7, 13),
        date(2026, 7, 14),
        date(2026, 7, 17),
        Strategy.SHORT_STRANGLE,
        100,
        90,
        105,
    )
    result = HistoricalTradeManagementContextLoader(
        EarningsDates(), Prices(), minimum_observations=1
    ).load(entry, date(2026, 7, 15), 109)

    assert result.total_observation_count == 2
    assert result.observation_count <= result.total_observation_count
