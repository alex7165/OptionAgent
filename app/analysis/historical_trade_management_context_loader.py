from __future__ import annotations

from datetime import date, timedelta

from app.analysis.entry_decision_snapshot import EntryDecisionSnapshot
from app.analysis.management_outcome_collection import ManagementOutcomeCollection
from app.analysis.management_strategy import ManagementStrategy
from app.analysis.strategies.close_day1_strategy import CloseDay1Strategy
from app.analysis.strategies.hold_to_friday_strategy import HoldToFridayStrategy
from app.analysis.strategies.roll_to_new_strike_strategy import (
    RollToNewStrikeStrategy,
)
from app.analysis.trade_manager_advisor import (
    ComparableManagementCase,
    HistoricalManagementContext,
)
from app.marketdata.historical_earnings_date_provider import (
    HistoricalEarningsDateProvider,
)
from app.marketdata.price_history_provider import DailyBar, PriceHistoryProvider


class HistoricalTradeManagementContextLoader:
    """Build management context from prior earnings without future leakage.

    Comparable cases are historical earnings events where the first market
    reaction session breached the original short-call distance. Later price
    action through Friday is used only to describe the outcome of that case.
    """

    def __init__(
        self,
        earnings_date_provider: HistoricalEarningsDateProvider,
        price_history_provider: PriceHistoryProvider,
        minimum_observations: int = 3,
        management_strategies: tuple[ManagementStrategy, ...] | None = None,
    ) -> None:
        if minimum_observations < 1:
            raise ValueError("minimum_observations must be at least one")
        self.earnings_date_provider = earnings_date_provider
        self.price_history_provider = price_history_provider
        self.minimum_observations = minimum_observations
        self.management_strategies = management_strategies or (
            CloseDay1Strategy(),
            HoldToFridayStrategy(),
            RollToNewStrikeStrategy(),
        )

    def load(
        self,
        entry: EntryDecisionSnapshot,
        as_of_date: date,
        current_price: float,
    ) -> HistoricalManagementContext:
        call_distance = entry.short_call_strike / entry.reference_price - 1
        # Historical comparability is defined by the trade that was actually
        # chosen: include every earnings event whose first reaction-session
        # high moved beyond the original short-call distance. Later moves and
        # the size of the current GS move are not additional selection filters.

        report_dates = tuple(
            item
            for item in self.earnings_date_provider.get_report_dates(entry.symbol)
            if item < entry.report_date
        )
        all_history = self._load_all_history(entry.symbol, report_dates, entry.report_date)

        finishes_inside: list[bool] = []
        continues_higher: list[bool] = []
        remaining_moves: list[float] = []
        comparable_cases: list[ComparableManagementCase] = []
        management_outcomes: list[ManagementOutcomeCollection] = []
        total_observation_count = 0

        for report_date in report_dates:
            friday = report_date + timedelta(days=(4 - report_date.weekday()) % 7)
            bars = self._event_bars(
                entry.symbol,
                report_date,
                friday,
                all_history,
            )
            prior = [bar for bar in bars if bar.date < report_date]
            if not prior:
                continue

            reference = prior[-1].close
            reaction = self._reaction_bar(entry.symbol, report_date, bars)
            if reaction is None:
                continue

            after_reaction = [bar for bar in bars if bar.date >= reaction.date]
            if not after_reaction:
                continue

            expiry = after_reaction[-1]
            total_observation_count += 1

            max_bar = max(after_reaction, key=lambda bar: bar.high)
            maximum_move = max_bar.high / reference - 1

            first_reaction_move = reaction.high / reference - 1

            # Select only cases in which the chosen short call would have been
            # breached during the first market reaction session after earnings.
            # Once selected, the case remains in the sample even if the stock
            # subsequently falls back below the strike by Friday.
            if first_reaction_move <= call_distance:
                continue

            finishes_inside.append(expiry.close / reference - 1 <= call_distance)
            continues_higher.append(expiry.close > reaction.close)
            remaining_moves.append((expiry.close / reaction.close - 1) * 100)

            max_day = after_reaction.index(max_bar) + 1
            prior_highs = [bar.high for bar in all_history if bar.date < report_date]
            made_all_time_high = bool(prior_highs) and max_bar.high > max(prior_highs)
            comparable_cases.append(
                ComparableManagementCase(
                    report_date=report_date,
                    maximum_move_percent=maximum_move * 100,
                    maximum_move_trading_day=max_day,
                    friday_close_move_percent=(expiry.close / reference - 1) * 100,
                    made_all_time_high=made_all_time_high,
                )
            )
            management_outcomes.append(
                self._build_management_outcomes(
                    entry=entry,
                    report_date=report_date,
                    reference_price=reference,
                    reaction_bar=reaction,
                    after_reaction=tuple(after_reaction),
                    made_all_time_high=made_all_time_high,
                )
            )

        count = len(finishes_inside)
        cases = tuple(sorted(comparable_cases, key=lambda item: item.report_date, reverse=True))
        if count < self.minimum_observations:
            return HistoricalManagementContext(
                count,
                None,
                None,
                None,
                total_observation_count,
                cases,
                tuple(
                    sorted(
                        management_outcomes,
                        key=lambda item: item.earnings_date,
                        reverse=True,
                    )
                ),
            )

        return HistoricalManagementContext(
            observation_count=count,
            probability_finish_back_inside=sum(finishes_inside) / count,
            probability_continue_higher=sum(continues_higher) / count,
            average_remaining_move_percent=sum(remaining_moves) / count,
            total_observation_count=total_observation_count,
            comparable_cases=cases,
            management_outcomes=tuple(
                sorted(
                    management_outcomes,
                    key=lambda item: item.earnings_date,
                    reverse=True,
                )
            ),
        )

    def _build_management_outcomes(
        self,
        *,
        entry: EntryDecisionSnapshot,
        report_date: date,
        reference_price: float,
        reaction_bar: DailyBar,
        after_reaction: tuple[DailyBar, ...],
        made_all_time_high: bool,
    ) -> ManagementOutcomeCollection:
        outcomes = tuple(
            strategy.simulate(
                entry=entry,
                report_date=report_date,
                reference_price=reference_price,
                reaction_bar=reaction_bar,
                after_reaction=after_reaction,
                made_all_time_high=made_all_time_high,
            )
            for strategy in self.management_strategies
        )
        return ManagementOutcomeCollection(
            symbol=entry.symbol,
            earnings_date=report_date,
            reference_price=reference_price,
            outcomes=outcomes,
        )

    def _reaction_bar(
        self,
        symbol: str,
        report_date: date,
        bars: tuple[DailyBar, ...],
    ) -> DailyBar | None:
        timing = self._report_timing(symbol, report_date)
        if timing in {"after_market_close", "after close", "amc"}:
            candidates = [bar for bar in bars if bar.date > report_date]
        else:
            candidates = [bar for bar in bars if bar.date >= report_date]
        return candidates[0] if candidates else None

    def _report_timing(self, symbol: str, report_date: date) -> str | None:
        getter = getattr(self.earnings_date_provider, "get_report_timing", None)
        if getter is None:
            return None
        timing = getter(symbol, report_date)
        if timing is None:
            return None
        value = getattr(timing, "value", timing)
        return str(value).strip().lower().replace("-", "_")

    def _load_all_history(
        self,
        symbol: str,
        report_dates: tuple[date, ...],
        current_report_date: date,
    ) -> tuple[DailyBar, ...]:
        if not report_dates:
            return ()
        return self.price_history_provider.get_daily_bars(
            symbol,
            date(1900, 1, 1),
            current_report_date - timedelta(days=1),
        )

    def _event_bars(
        self,
        symbol: str,
        report_date: date,
        friday: date,
        all_history: tuple[DailyBar, ...],
    ) -> tuple[DailyBar, ...]:
        selected = tuple(
            bar
            for bar in all_history
            if report_date - timedelta(days=7) <= bar.date <= friday
        )
        if selected:
            return selected
        return self.price_history_provider.get_daily_bars(
            symbol,
            report_date - timedelta(days=7),
            friday,
        )
