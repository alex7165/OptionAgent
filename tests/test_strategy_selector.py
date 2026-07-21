from datetime import date

from app.analysis.expected_move import ExpectedMove
from app.analysis.historical_strike_adjusted_selector import (
    HistoricalStrikeAdjustedSelection,
    HistoricalStrikeAdjustment,
)
from app.analysis.historical_strike_selector import (
    HistoricalStrikeSelectionPolicy,
)
from app.analysis.historical_strategy_selector_adapter import (
    HistoricalStrategySelectionResult,
)
from app.analysis.strategy import Strategy
from app.analysis.strategy_selector import StrategySelector
from app.analysis.strike_selection import StrikeSelection
from app.marketdata.models import ExpirationChain


class RecordingStrikeSelector:

    def __init__(self, result: StrikeSelection) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def select_by_expected_move(
        self,
        *,
        chain: ExpirationChain,
        expected_move: ExpectedMove,
        strategy: Strategy,
    ) -> StrikeSelection:
        self.calls.append(
            {
                "chain": chain,
                "expected_move": expected_move,
                "strategy": strategy,
            }
        )
        return self.result


class RecordingHistoricalAdapter:

    def __init__(
        self,
        strike_selection: StrikeSelection,
    ) -> None:
        self.strike_selection = strike_selection
        self.calls: list[dict[str, object]] = []

    def select(self, **kwargs: object) -> HistoricalStrategySelectionResult:
        self.calls.append(kwargs)
        return HistoricalStrategySelectionResult(
            historical_result=object(),
            adjusted_selection=HistoricalStrikeAdjustedSelection(
                adjustment=HistoricalStrikeAdjustment(
                    expected_move_percent=10.0,
                    put_percent=0.12,
                    call_percent=0.15,
                    put_was_adjusted=True,
                    call_was_adjusted=True,
                ),
                strike_selection=self.strike_selection,
            ),
        )


def make_chain() -> ExpirationChain:
    return ExpirationChain(
        symbol="NVDA",
        expiration=date(2026, 7, 17),
        quotes=[],
    )


def make_expected_move() -> ExpectedMove:
    return ExpectedMove(
        percent=0.10,
        up_price=220.0,
        down_price=180.0,
    )


def make_strike_selection(
    strategy: Strategy = Strategy.IRON_CONDOR,
) -> StrikeSelection:
    return StrikeSelection(
        put=None,
        call=None,
        put_target=180.0,
        call_target=220.0,
        strategy=strategy,
    )


def test_selects_strikes_with_existing_behavior_without_adapter() -> None:
    chain = make_chain()
    expected_move = make_expected_move()
    expected_selection = make_strike_selection(
        strategy=Strategy.SHORT_STRANGLE
    )
    strike_selector = RecordingStrikeSelector(
        result=expected_selection
    )
    selector = StrategySelector(
        strike_selector=strike_selector,
    )

    result = selector.select_strikes(
        chain=chain,
        underlying_price=200.0,
        expected_move=expected_move,
        strategy=Strategy.SHORT_STRANGLE,
    )

    assert result is expected_selection
    assert strike_selector.calls == [
        {
            "chain": chain,
            "expected_move": expected_move,
            "strategy": Strategy.SHORT_STRANGLE,
        }
    ]


def test_uses_historical_adapter_when_present() -> None:
    chain = make_chain()
    expected_move = make_expected_move()
    expected_selection = make_strike_selection()
    historical_adapter = RecordingHistoricalAdapter(
        strike_selection=expected_selection
    )
    fallback_selector = RecordingStrikeSelector(
        result=make_strike_selection()
    )
    selector = StrategySelector(
        strike_selector=fallback_selector,
        historical_adapter=historical_adapter,
    )
    price_analyses = (object(),)
    policy = HistoricalStrikeSelectionPolicy(
        max_finish_outside_probability=0.10,
    )

    result = selector.select_strikes(
        chain=chain,
        underlying_price=200.0,
        expected_move=expected_move,
        price_analyses=price_analyses,
        exit_trading_day_index=2,
        call_thresholds=(7.5, 10.0, 12.5),
        put_thresholds=(-7.5, -10.0, -12.5),
        policy=policy,
    )

    assert result is expected_selection
    assert fallback_selector.calls == []
    assert historical_adapter.calls == [
        {
            "chain": chain,
            "underlying_price": 200.0,
            "expected_move": expected_move,
            "price_analyses": price_analyses,
            "exit_trading_day_index": 2,
            "call_thresholds": (7.5, 10.0, 12.5),
            "put_thresholds": (-7.5, -10.0, -12.5),
            "policy": policy,
            "strategy": Strategy.IRON_CONDOR,
        }
    ]
