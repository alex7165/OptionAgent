from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.analysis.backtest_outcome_analyzer import (
    BacktestOutcome,
    BacktestOutcomeAnalyzer,
)
from app.analysis.repair_strategy_backtest import (
    RepairStrategyBacktestAnalyzer,
    RepairStrategyOutcome,
)
from app.analysis.strike_selection import StrikeSelection
from app.analysis.strategy import Strategy
from app.analysis.entry_decision_snapshot import EntryDecisionSnapshot
from app.marketdata.models import OptionQuote
from app.marketdata.price_history_provider import PriceHistoryProvider


@dataclass(frozen=True, slots=True)
class TradeSnapshot:
    symbol: str
    decision_date: date
    report_date: date
    reference_price: float
    short_put_strike: float
    short_call_strike: float
    expiration: date = date(2026, 7, 17)
    strategy: Strategy = Strategy.SHORT_STRANGLE

    @classmethod
    def from_entry_decision(cls, snapshot: EntryDecisionSnapshot) -> "TradeSnapshot":
        return cls(
            symbol=snapshot.symbol,
            decision_date=snapshot.decision_date,
            report_date=snapshot.report_date,
            reference_price=snapshot.reference_price,
            short_put_strike=snapshot.short_put_strike,
            short_call_strike=snapshot.short_call_strike,
            expiration=snapshot.expiration,
            strategy=snapshot.strategy,
        )


@dataclass(frozen=True, slots=True)
class TradeSnapshotReview:
    snapshot: TradeSnapshot
    outcomes: tuple[BacktestOutcome, ...]
    repair: RepairStrategyOutcome


class TradeSnapshotReviewRunner:
    """Review stored strike snapshots against later underlying prices."""

    def __init__(
        self,
        price_history_provider: PriceHistoryProvider,
        outcome_analyzer: BacktestOutcomeAnalyzer | None = None,
        repair_analyzer: RepairStrategyBacktestAnalyzer | None = None,
    ) -> None:
        self.price_history_provider = price_history_provider
        self.outcome_analyzer = outcome_analyzer or BacktestOutcomeAnalyzer()
        self.repair_analyzer = repair_analyzer or RepairStrategyBacktestAnalyzer()

    def run(
        self,
        snapshots: tuple[TradeSnapshot, ...],
        end_date: date,
    ) -> tuple[TradeSnapshotReview, ...]:
        reviews: list[TradeSnapshotReview] = []
        for snapshot in snapshots:
            bars = self.price_history_provider.get_daily_bars(
                snapshot.symbol,
                snapshot.report_date,
                end_date,
            )
            if not bars:
                continue

            selection = self._selection(snapshot)
            outcomes = tuple(
                self.outcome_analyzer.analyze(
                    selection=selection,
                    daily_bars=bars,
                    reference_price=snapshot.reference_price,
                    exit_trading_day_index=index,
                )
                for index in range(1, len(bars) + 1)
            )
            repair = self.repair_analyzer.analyze(
                selection=selection,
                daily_bars=bars,
                reference_price=snapshot.reference_price,
            )
            reviews.append(
                TradeSnapshotReview(
                    snapshot=snapshot,
                    outcomes=outcomes,
                    repair=repair,
                )
            )
        return tuple(reviews)

    @staticmethod
    def _selection(snapshot: TradeSnapshot) -> StrikeSelection:
        return StrikeSelection(
            put=OptionQuote(
                symbol=snapshot.symbol,
                expiration=snapshot.expiration,
                strike=snapshot.short_put_strike,
                option_type="put",
            ),
            call=OptionQuote(
                symbol=snapshot.symbol,
                expiration=snapshot.expiration,
                strike=snapshot.short_call_strike,
                option_type="call",
            ),
            put_target=snapshot.short_put_strike,
            call_target=snapshot.short_call_strike,
            strategy=snapshot.strategy,
        )
