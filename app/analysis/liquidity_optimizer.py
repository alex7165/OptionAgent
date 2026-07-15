from __future__ import annotations

from dataclasses import replace

from app.analysis.earnings_crush_rules import EarningsCrushRules
from app.analysis.strike_selection import StrikeSelection
from app.analysis.strategy import Strategy
from app.analysis.wing_selector import WingSelector
from app.marketdata.models import ExpirationChain, OptionQuote


class LiquidityOptimizer:
    """Move short legs to an adjacent strike only for clearly better liquidity."""

    MIN_OPEN_INTEREST_IMPROVEMENT = 3.0
    MAX_OUTWARD_STEPS = 2

    def __init__(self) -> None:
        self.wing_selector = WingSelector()

    def optimize(
        self,
        selection: StrikeSelection,
        chain: ExpirationChain,
        underlying_price: float | None = None,
    ) -> StrikeSelection:
        self._validate_short_legs(selection)

        put = self._optimize_leg(
            selection.put,
            chain,
            "put",
        )
        call = self._optimize_leg(
            selection.call,
            chain,
            "call",
        )

        if put is selection.put and call is selection.call:
            return selection

        long_put = selection.long_put
        long_call = selection.long_call

        if selection.strategy is Strategy.IRON_CONDOR:
            long_put = self._select_long_put(selection, chain, put)
            long_call = self._select_long_call(selection, chain, call)

        optimized = replace(
            selection,
            put=put,
            call=call,
            long_put=long_put,
            long_call=long_call,
        )
        self._validate_short_legs(optimized)
        return optimized

    @staticmethod
    def _validate_short_legs(selection: StrikeSelection) -> None:
        if selection.put is None or selection.call is None:
            return

        if selection.put.strike >= selection.call.strike:
            raise ValueError(
                "short put strike must be below short call strike"
            )

    def _optimize_leg(
        self,
        current: OptionQuote | None,
        chain: ExpirationChain,
        option_type: str,
    ) -> OptionQuote | None:
        if current is None:
            return None

        quotes = sorted(
            (
                quote
                for quote in chain.quotes
                if quote.option_type == option_type
            ),
            key=lambda quote: quote.strike,
        )

        try:
            index = quotes.index(current)
        except ValueError:
            return current

        candidates = self._outward_candidates(
            quotes,
            index,
            option_type,
        )
        improvements = [
            (steps, candidate)
            for steps, candidate in candidates
            if self._is_clear_improvement(candidate, current)
        ]
        if not improvements:
            return current

        _, best = max(
            improvements,
            key=lambda item: self._liquidity_score(
                item[1],
                outward_steps=item[0],
            ),
        )
        return best

    def _outward_candidates(
        self,
        quotes: list[OptionQuote],
        index: int,
        option_type: str,
    ) -> list[tuple[int, OptionQuote]]:
        if option_type == "put":
            return [
                (steps, quotes[index - steps])
                for steps in range(1, self.MAX_OUTWARD_STEPS + 1)
                if index - steps >= 0
            ]

        if option_type == "call":
            return [
                (steps, quotes[index + steps])
                for steps in range(1, self.MAX_OUTWARD_STEPS + 1)
                if index + steps < len(quotes)
            ]

        raise ValueError(f"unsupported option type: {option_type}")

    def _liquidity_score(
        self,
        quote: OptionQuote,
        *,
        outward_steps: int,
    ) -> tuple[int, int, int, int, float, int, int, int]:
        spread = quote.bid_ask_spread_percent
        spread_score = -(spread if spread is not None else float("inf"))
        return (
            self._passed_check_count(quote),
            int(self._spread_ok(quote)),
            int(self._open_interest_ok(quote)),
            int(self._volume_ok(quote)),
            spread_score,
            quote.open_interest or 0,
            quote.volume or 0,
            -outward_steps,
        )

    def _is_clear_improvement(
        self,
        candidate: OptionQuote,
        current: OptionQuote,
    ) -> bool:
        candidate_checks = self._passed_check_count(candidate)
        current_checks = self._passed_check_count(current)

        if candidate_checks > current_checks:
            return True

        if candidate_checks < current_checks:
            return False

        if not self._same_threshold_status(candidate, current):
            return False

        current_oi = current.open_interest or 0
        candidate_oi = candidate.open_interest or 0

        if current_oi <= 0:
            return candidate_oi > 0

        return (
            candidate_oi
            >= current_oi * self.MIN_OPEN_INTEREST_IMPROVEMENT
        )

    @staticmethod
    def _passed_check_count(quote: OptionQuote) -> int:
        return sum(
            (
                LiquidityOptimizer._spread_ok(quote),
                LiquidityOptimizer._open_interest_ok(quote),
                LiquidityOptimizer._volume_ok(quote),
            )
        )

    @staticmethod
    def _same_threshold_status(
        first: OptionQuote,
        second: OptionQuote,
    ) -> bool:
        return (
            LiquidityOptimizer._spread_ok(first)
            == LiquidityOptimizer._spread_ok(second)
            and LiquidityOptimizer._volume_ok(first)
            == LiquidityOptimizer._volume_ok(second)
        )

    @staticmethod
    def _spread_ok(quote: OptionQuote) -> bool:
        spread = quote.bid_ask_spread_percent
        return (
            spread is not None
            and spread <= EarningsCrushRules.MAX_BID_ASK_SPREAD
        )

    @staticmethod
    def _open_interest_ok(quote: OptionQuote) -> bool:
        return (
            quote.open_interest is not None
            and quote.open_interest
            >= EarningsCrushRules.MIN_OPEN_INTEREST
        )

    @staticmethod
    def _volume_ok(quote: OptionQuote) -> bool:
        return (
            quote.volume is not None
            and quote.volume >= EarningsCrushRules.MIN_VOLUME
        )

    def _select_long_put(
        self,
        selection: StrikeSelection,
        chain: ExpirationChain,
        short_put: OptionQuote | None,
    ) -> OptionQuote | None:
        if short_put is None:
            return None

        width = self._put_wing_width(selection)
        if width is None:
            width = self._automatic_wing_width(selection)

        return self.wing_selector.select_long_put(
            chain,
            short_put,
            width,
        )

    def _select_long_call(
        self,
        selection: StrikeSelection,
        chain: ExpirationChain,
        short_call: OptionQuote | None,
    ) -> OptionQuote | None:
        if short_call is None:
            return None

        width = self._call_wing_width(selection)
        if width is None:
            width = self._automatic_wing_width(selection)

        return self.wing_selector.select_long_call(
            chain,
            short_call,
            width,
        )

    @staticmethod
    def _put_wing_width(
        selection: StrikeSelection,
    ) -> float | None:
        if selection.put is None or selection.long_put is None:
            return None
        return selection.put.strike - selection.long_put.strike

    @staticmethod
    def _call_wing_width(
        selection: StrikeSelection,
    ) -> float | None:
        if selection.call is None or selection.long_call is None:
            return None
        return selection.long_call.strike - selection.call.strike

    def _automatic_wing_width(
        self,
        selection: StrikeSelection,
    ) -> float:
        underlying_price = (
            selection.put_target + selection.call_target
        ) / 2
        return self.wing_selector.width_for_price(underlying_price)
