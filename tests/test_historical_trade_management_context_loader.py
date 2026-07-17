import pytest
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
            DailyBar(date(year, 7, 15), 108, 110, 107, 109, 1),
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


def test_reports_compact_details_for_each_comparable_case():
    class Dates:
        def get_report_dates(self, symbol):
            return (date(2025, 7, 15),)

    class FullPrices:
        def get_daily_bars(self, symbol, start_date, end_date):
            return (
                DailyBar(date(2024, 1, 2), 80, 90, 79, 85, 1),
                DailyBar(date(2025, 7, 14), 100, 101, 99, 100, 1),
                DailyBar(date(2025, 7, 15), 108, 110, 107, 109, 1),
                DailyBar(date(2025, 7, 16), 108, 112, 107, 109, 1),
                DailyBar(date(2025, 7, 17), 109, 111, 108, 110, 1),
                DailyBar(date(2025, 7, 18), 110, 111, 109, 110, 1),
            )

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
        Dates(), FullPrices(), minimum_observations=1
    ).load(entry, date(2026, 7, 15), 109)

    case = result.comparable_cases[0]
    assert case.report_date == date(2025, 7, 15)
    assert case.maximum_move_percent == pytest.approx(12.0)
    assert case.maximum_move_trading_day == 2
    assert case.friday_close_move_percent == pytest.approx(10.0)
    assert case.made_all_time_high is True


def test_selects_case_on_first_reaction_day_even_if_it_falls_by_friday():
    class Dates:
        def get_report_dates(self, symbol):
            return (date(2025, 7, 15),)

    class ReversalPrices:
        def get_daily_bars(self, symbol, start_date, end_date):
            return (
                DailyBar(date(2025, 7, 14), 100, 101, 99, 100, 1),
                DailyBar(date(2025, 7, 15), 109, 111, 108, 109, 1),
                DailyBar(date(2025, 7, 16), 106, 107, 104, 105, 1),
                DailyBar(date(2025, 7, 17), 103, 104, 101, 102, 1),
                DailyBar(date(2025, 7, 18), 101, 102, 99, 100, 1),
            )

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
        Dates(), ReversalPrices(), minimum_observations=1
    ).load(entry, date(2026, 7, 16), 110)

    assert result.observation_count == 1
    assert result.probability_finish_back_inside == 1.0
    assert result.probability_continue_higher == 0.0
    assert result.average_remaining_move_percent < 0
    assert result.comparable_cases[0].friday_close_move_percent == pytest.approx(0.0)


def test_after_market_close_uses_next_trading_session_as_reaction_day():
    class Dates:
        def get_report_dates(self, symbol):
            return (date(2025, 7, 15),)

        def get_report_timing(self, symbol, report_date):
            return "after_market_close"

    class AfterClosePrices:
        def get_daily_bars(self, symbol, start_date, end_date):
            return (
                DailyBar(date(2025, 7, 14), 100, 101, 99, 100, 1),
                DailyBar(date(2025, 7, 15), 100, 101, 99, 100, 1),
                DailyBar(date(2025, 7, 16), 109, 111, 108, 109, 1),
                DailyBar(date(2025, 7, 17), 108, 110, 106, 107, 1),
                DailyBar(date(2025, 7, 18), 106, 108, 104, 105, 1),
            )

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
        Dates(), AfterClosePrices(), minimum_observations=1
    ).load(entry, date(2026, 7, 16), 110)

    assert result.observation_count == 1
    assert result.comparable_cases[0].maximum_move_trading_day == 1
    assert result.comparable_cases[0].friday_close_move_percent == pytest.approx(5.0)


def test_excludes_case_that_breaches_short_call_only_after_first_reaction_day():
    class Dates:
        def get_report_dates(self, symbol):
            return (date(2025, 7, 15),)

    class LaterBreachPrices:
        def get_daily_bars(self, symbol, start_date, end_date):
            return (
                DailyBar(date(2025, 7, 14), 100, 101, 99, 100, 1),
                DailyBar(date(2025, 7, 15), 103, 104, 102, 103, 1),
                DailyBar(date(2025, 7, 16), 104, 106, 103, 105, 1),
                DailyBar(date(2025, 7, 17), 102, 103, 101, 102, 1),
                DailyBar(date(2025, 7, 18), 100, 101, 99, 100, 1),
            )

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

    # The first reaction-session high is only +4%. A later +6% high does not
    # make the case comparable because selection must use the first reaction day.
    result = HistoricalTradeManagementContextLoader(
        Dates(), LaterBreachPrices(), minimum_observations=1
    ).load(entry, date(2026, 7, 16), 110)

    assert result.observation_count == 0
    assert result.total_observation_count == 1
    assert result.comparable_cases == ()


def test_does_not_use_current_move_as_comparability_filter():
    class Dates:
        def get_report_dates(self, symbol):
            return (date(2025, 7, 15),)

    class StrikeBreachPrices:
        def get_daily_bars(self, symbol, start_date, end_date):
            return (
                DailyBar(date(2025, 7, 14), 100, 101, 99, 100, 1),
                DailyBar(date(2025, 7, 15), 105, 106, 104, 105, 1),
                DailyBar(date(2025, 7, 16), 104, 105, 103, 104, 1),
                DailyBar(date(2025, 7, 17), 103, 104, 102, 103, 1),
                DailyBar(date(2025, 7, 18), 102, 103, 101, 102, 1),
            )

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

    # Current GS is +20%, but the historical case is still comparable because
    # its post-earnings high exceeded the selected +5% short call.
    result = HistoricalTradeManagementContextLoader(
        Dates(), StrikeBreachPrices(), minimum_observations=1
    ).load(entry, date(2026, 7, 16), 120)

    assert result.observation_count == 1
    assert result.comparable_cases[0].maximum_move_percent == pytest.approx(6.0)
