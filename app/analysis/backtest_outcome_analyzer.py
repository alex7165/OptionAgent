from dataclasses import dataclass
from datetime import date

from app.analysis.strike_selection import StrikeSelection
from app.marketdata.price_history_provider import DailyBar


@dataclass(frozen=True, slots=True)
class BacktestOutcome:
    exit_trading_day_index: int
    exit_date: date
    exit_close: float
    short_put_strike: float
    short_call_strike: float
    put_touched: bool
    call_touched: bool
    put_finished_outside: bool
    call_finished_outside: bool
    finished_inside_short_strikes: bool
    max_adverse_move_percent: float
    max_favorable_move_percent: float
    holding_days: int


class BacktestOutcomeAnalyzer:
    """Evaluate an already selected trade against later underlying bars.

    This analyzer intentionally evaluates underlying-price outcomes only. It
    does not estimate option P&L because historical option premiums and closes
    are not part of the current data model.
    """

    def analyze(
        self,
        selection: StrikeSelection,
        daily_bars: tuple[DailyBar, ...],
        reference_price: float,
        exit_trading_day_index: int,
    ) -> BacktestOutcome:
        if selection.put is None or selection.call is None:
            raise ValueError("selection must contain both short strikes")

        if reference_price <= 0:
            raise ValueError("reference_price must be greater than zero")

        if exit_trading_day_index <= 0:
            raise ValueError("exit_trading_day_index must be greater than zero")

        if len(daily_bars) < exit_trading_day_index:
            raise ValueError(
                "daily_bars do not contain the requested exit trading day"
            )

        if any(
            current.date >= following.date
            for current, following in zip(daily_bars, daily_bars[1:])
        ):
            raise ValueError(
                "daily_bars must be ordered by ascending unique date"
            )

        evaluated_bars = daily_bars[:exit_trading_day_index]
        exit_bar = evaluated_bars[-1]
        put_strike = selection.put.strike
        call_strike = selection.call.strike

        lowest_low = min(bar.low for bar in evaluated_bars)
        highest_high = max(bar.high for bar in evaluated_bars)

        put_touched = lowest_low <= put_strike
        call_touched = highest_high >= call_strike
        put_finished_outside = exit_bar.close < put_strike
        call_finished_outside = exit_bar.close > call_strike

        return BacktestOutcome(
            exit_trading_day_index=exit_trading_day_index,
            exit_date=exit_bar.date,
            exit_close=exit_bar.close,
            short_put_strike=put_strike,
            short_call_strike=call_strike,
            put_touched=put_touched,
            call_touched=call_touched,
            put_finished_outside=put_finished_outside,
            call_finished_outside=call_finished_outside,
            finished_inside_short_strikes=(
                not put_finished_outside and not call_finished_outside
            ),
            max_adverse_move_percent=(
                lowest_low / reference_price - 1
            ) * 100,
            max_favorable_move_percent=(
                highest_high / reference_price - 1
            ) * 100,
            holding_days=exit_trading_day_index,
        )
