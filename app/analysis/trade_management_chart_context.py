from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from statistics import mean

from app.analysis.entry_decision_snapshot import EntryDecisionSnapshot
from app.marketdata.price_history_provider import DailyBar, PriceHistoryProvider


@dataclass(frozen=True, slots=True)
class TradeManagementChartContext:
    as_of_trading_date: date
    current_close: float
    return_since_entry_percent: float
    gap_from_pre_earnings_close_percent: float | None
    distance_to_prior_high_percent: float | None
    is_new_period_high: bool
    close_location_percent: float | None
    volume_ratio_20d: float | None
    above_sma20: bool | None
    above_sma50: bool | None
    atr14_percent: float | None
    gap_held: bool | None
    revaluation_signal_count: int


class TradeManagementChartContextAnalyzer:
    """Describe the current post-earnings chart without future leakage."""

    def __init__(
        self,
        price_history_provider: PriceHistoryProvider,
        lookback_days: int = 5 * 366,
    ) -> None:
        self.price_history_provider = price_history_provider
        self.lookback_days = lookback_days

    def analyze(
        self,
        entry: EntryDecisionSnapshot,
        as_of_date: date,
    ) -> TradeManagementChartContext:
        if as_of_date < entry.report_date:
            raise ValueError("as_of_date must not be before report_date")
        bars = self.price_history_provider.get_daily_bars(
            entry.symbol,
            as_of_date - timedelta(days=self.lookback_days),
            as_of_date,
        )
        if not bars:
            raise ValueError("current_chart_history_unavailable")

        current = bars[-1]
        previous = bars[:-1]
        prior_high = max((bar.high for bar in previous), default=None)
        pre_earnings = [bar for bar in bars if bar.date < entry.report_date]
        post_earnings = [bar for bar in bars if entry.report_date <= bar.date <= current.date]
        pre_close = pre_earnings[-1].close if pre_earnings else None

        gap_percent = (
            (post_earnings[0].open / pre_close - 1) * 100
            if pre_close is not None and post_earnings
            else None
        )
        distance_to_prior_high = (
            (current.close / prior_high - 1) * 100
            if prior_high not in (None, 0)
            else None
        )
        day_range = current.high - current.low
        close_location = (
            (current.close - current.low) / day_range * 100
            if day_range > 0
            else None
        )
        recent_volumes = [bar.volume for bar in previous[-20:] if bar.volume > 0]
        volume_ratio = (
            current.volume / mean(recent_volumes)
            if current.volume > 0 and recent_volumes
            else None
        )
        sma20 = mean(bar.close for bar in bars[-20:]) if len(bars) >= 20 else None
        sma50 = mean(bar.close for bar in bars[-50:]) if len(bars) >= 50 else None
        atr_percent = self._atr_percent(bars[-15:])
        gap_held = (
            min(bar.low for bar in post_earnings) > pre_close
            if pre_close is not None and post_earnings and gap_percent is not None and gap_percent > 0
            else None
        )
        is_new_high = prior_high is not None and current.high >= prior_high

        signals = sum(
            (
                bool(is_new_high),
                close_location is not None and close_location >= 75,
                volume_ratio is not None and volume_ratio >= 1.5,
                gap_held is True,
                sma20 is not None and current.close > sma20,
                sma50 is not None and current.close > sma50,
            )
        )
        return TradeManagementChartContext(
            as_of_trading_date=current.date,
            current_close=current.close,
            return_since_entry_percent=(current.close / entry.reference_price - 1) * 100,
            gap_from_pre_earnings_close_percent=gap_percent,
            distance_to_prior_high_percent=distance_to_prior_high,
            is_new_period_high=is_new_high,
            close_location_percent=close_location,
            volume_ratio_20d=volume_ratio,
            above_sma20=(current.close > sma20 if sma20 is not None else None),
            above_sma50=(current.close > sma50 if sma50 is not None else None),
            atr14_percent=atr_percent,
            gap_held=gap_held,
            revaluation_signal_count=signals,
        )

    @staticmethod
    def _atr_percent(bars: tuple[DailyBar, ...] | list[DailyBar]) -> float | None:
        if len(bars) < 2:
            return None
        true_ranges: list[float] = []
        for previous, current in zip(bars, bars[1:]):
            true_ranges.append(
                max(
                    current.high - current.low,
                    abs(current.high - previous.close),
                    abs(current.low - previous.close),
                )
            )
        if not true_ranges or bars[-1].close <= 0:
            return None
        return mean(true_ranges) / bars[-1].close * 100
