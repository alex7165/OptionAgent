from __future__ import annotations

from datetime import date, timedelta

from app.analysis.entry_decision_snapshot import EntryDecisionSnapshot
from app.analysis.trade_manager_advisor import HistoricalManagementContext
from app.marketdata.historical_earnings_date_provider import (
    HistoricalEarningsDateProvider,
)
from app.marketdata.price_history_provider import PriceHistoryProvider


class HistoricalTradeManagementContextLoader:
    """Build management context from prior earnings without future leakage.

    The loader depends only on prior earnings dates and underlying price
    history. It deliberately has no dependency on the Earnings API used by
    the entry workflow.
    """

    def __init__(
        self,
        earnings_date_provider: HistoricalEarningsDateProvider,
        price_history_provider: PriceHistoryProvider,
        minimum_observations: int = 3,
    ) -> None:
        if minimum_observations < 1:
            raise ValueError("minimum_observations must be at least one")
        self.earnings_date_provider = earnings_date_provider
        self.price_history_provider = price_history_provider
        self.minimum_observations = minimum_observations

    def load(
        self,
        entry: EntryDecisionSnapshot,
        as_of_date: date,
        current_price: float,
    ) -> HistoricalManagementContext:
        observation_day = max(1, (as_of_date - entry.report_date).days + 1)
        call_distance = entry.short_call_strike / entry.reference_price - 1
        current_return = current_price / entry.reference_price - 1

        finishes_inside: list[bool] = []
        total_observation_count = 0
        continues_higher: list[bool] = []
        remaining_moves: list[float] = []

        for report_date in self.earnings_date_provider.get_report_dates(
            entry.symbol
        ):
            if report_date >= entry.report_date:
                continue

            friday = report_date + timedelta(
                days=(4 - report_date.weekday()) % 7
            )
            bars = self.price_history_provider.get_daily_bars(
                entry.symbol,
                report_date - timedelta(days=7),
                friday,
            )
            prior = [bar for bar in bars if bar.date < report_date]
            after = [bar for bar in bars if bar.date >= report_date]
            if not prior or len(after) < observation_day:
                continue

            reference = prior[-1].close
            observed = after[observation_day - 1]
            expiry = after[-1]
            observed_return = observed.close / reference - 1
            total_observation_count += 1

            threshold = max(call_distance, current_return * 0.80)
            if observed_return < threshold:
                continue

            finishes_inside.append(
                expiry.close / reference - 1 <= call_distance
            )
            continues_higher.append(expiry.close > observed.close)
            remaining_moves.append(
                (expiry.close / observed.close - 1) * 100
            )

        count = len(finishes_inside)
        if count < self.minimum_observations:
            return HistoricalManagementContext(
                count, None, None, None, total_observation_count
            )

        return HistoricalManagementContext(
            observation_count=count,
            probability_finish_back_inside=(
                sum(finishes_inside) / count
            ),
            probability_continue_higher=(
                sum(continues_higher) / count
            ),
            average_remaining_move_percent=(
                sum(remaining_moves) / count
            ),
            total_observation_count=total_observation_count,
        )
