from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from typing import Protocol

from app.analysis.expected_move_analyzer import ExpectedMoveAnalyzer
from app.analysis.walk_forward_backtest_runner import WalkForwardBacktestCase
from app.marketdata.earnings_api_provider import HistoricalEarningsReaction
from app.marketdata.models import ExpirationChain
from app.marketdata.price_history_provider import DailyBar, PriceHistoryProvider


class HistoricalOptionChainProvider(Protocol):
    """Provide an option chain exactly as it was known on a past date."""

    def get_expiration_chain(
        self,
        symbol: str,
        expiration: date,
        as_of_date: date,
    ) -> ExpirationChain | None:
        ...


class HistoricalBacktestCaseSkipReason(str, Enum):
    REFERENCE_PRICE_UNAVAILABLE = "reference_price_unavailable"
    HISTORICAL_OPTION_CHAIN_UNAVAILABLE = "historical_option_chain_unavailable"
    EXPECTED_MOVE_UNAVAILABLE = "expected_move_unavailable"
    OUTCOME_PRICE_HISTORY_UNAVAILABLE = "outcome_price_history_unavailable"


@dataclass(frozen=True, slots=True)
class HistoricalBacktestCaseBuildResult:
    earnings: HistoricalEarningsReaction
    case: WalkForwardBacktestCase | None
    skip_reason: HistoricalBacktestCaseSkipReason | None
    as_of_date: date | None = None
    expiration: date | None = None

    @property
    def built(self) -> bool:
        return self.case is not None


class HistoricalBacktestCaseBuilder:
    """Build leakage-free walk-forward cases from historical market data.

    The builder never substitutes a synthetic expected move. A case is built
    only when an option chain for the actual pre-earnings trading date is
    available and contains a valid ATM straddle.
    """

    def __init__(
        self,
        price_history_provider: PriceHistoryProvider,
        historical_option_chain_provider: HistoricalOptionChainProvider,
        expected_move_analyzer: ExpectedMoveAnalyzer | None = None,
        reference_lookback_days: int = 10,
    ) -> None:
        if reference_lookback_days < 1:
            raise ValueError("reference_lookback_days must be at least 1")

        self.price_history_provider = price_history_provider
        self.historical_option_chain_provider = historical_option_chain_provider
        self.expected_move_analyzer = expected_move_analyzer or ExpectedMoveAnalyzer()
        self.reference_lookback_days = reference_lookback_days

    def build(
        self,
        earnings: HistoricalEarningsReaction,
    ) -> HistoricalBacktestCaseBuildResult:
        reference_bar = self._reference_bar(earnings)
        expiration = self._earnings_week_friday(earnings.report_date)

        if reference_bar is None or reference_bar.close <= 0:
            return HistoricalBacktestCaseBuildResult(
                earnings=earnings,
                case=None,
                skip_reason=(
                    HistoricalBacktestCaseSkipReason.REFERENCE_PRICE_UNAVAILABLE
                ),
                expiration=expiration,
            )

        chain = self.historical_option_chain_provider.get_expiration_chain(
            symbol=earnings.symbol,
            expiration=expiration,
            as_of_date=reference_bar.date,
        )
        if chain is None:
            return HistoricalBacktestCaseBuildResult(
                earnings=earnings,
                case=None,
                skip_reason=(
                    HistoricalBacktestCaseSkipReason.HISTORICAL_OPTION_CHAIN_UNAVAILABLE
                ),
                as_of_date=reference_bar.date,
                expiration=expiration,
            )

        expected_move = self.expected_move_analyzer.from_atm_straddle(
            chain=chain,
            underlying_price=reference_bar.close,
        )
        if expected_move is None:
            return HistoricalBacktestCaseBuildResult(
                earnings=earnings,
                case=None,
                skip_reason=(
                    HistoricalBacktestCaseSkipReason.EXPECTED_MOVE_UNAVAILABLE
                ),
                as_of_date=reference_bar.date,
                expiration=expiration,
            )

        daily_bars = self.price_history_provider.get_daily_bars(
            symbol=earnings.symbol,
            start_date=earnings.report_date,
            end_date=expiration,
        )
        usable_bars = tuple(
            sorted(
                (
                    bar
                    for bar in daily_bars
                    if earnings.report_date <= bar.date <= expiration
                ),
                key=lambda bar: bar.date,
            )
        )
        if not usable_bars:
            return HistoricalBacktestCaseBuildResult(
                earnings=earnings,
                case=None,
                skip_reason=(
                    HistoricalBacktestCaseSkipReason.OUTCOME_PRICE_HISTORY_UNAVAILABLE
                ),
                as_of_date=reference_bar.date,
                expiration=expiration,
            )

        return HistoricalBacktestCaseBuildResult(
            earnings=earnings,
            case=WalkForwardBacktestCase(
                report_date=earnings.report_date,
                chain=chain,
                expected_move=expected_move,
                reference_price=reference_bar.close,
                daily_bars=usable_bars,
            ),
            skip_reason=None,
            as_of_date=reference_bar.date,
            expiration=expiration,
        )

    def build_many(
        self,
        earnings: tuple[HistoricalEarningsReaction, ...],
    ) -> tuple[HistoricalBacktestCaseBuildResult, ...]:
        return tuple(
            self.build(item)
            for item in sorted(earnings, key=lambda value: value.report_date)
        )

    def _reference_bar(
        self,
        earnings: HistoricalEarningsReaction,
    ) -> DailyBar | None:
        end_date = earnings.report_date - timedelta(days=1)
        start_date = earnings.report_date - timedelta(
            days=self.reference_lookback_days
        )
        bars = self.price_history_provider.get_daily_bars(
            symbol=earnings.symbol,
            start_date=start_date,
            end_date=end_date,
        )
        eligible = tuple(
            bar for bar in bars if bar.date < earnings.report_date
        )
        if not eligible:
            return None
        return max(eligible, key=lambda bar: bar.date)

    @staticmethod
    def _earnings_week_friday(report_date: date) -> date:
        return report_date + timedelta(days=(4 - report_date.weekday()) % 7)
