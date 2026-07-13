from datetime import date
from types import SimpleNamespace

from app.analysis.earnings_crush_analyzer import EarningsCrushAnalyzer
from app.analysis.historical_strategy_selection_inputs import (
    HistoricalStrategySelectionInputs,
)
from app.analysis.expected_move import ExpectedMove
from app.analysis.historical_strike_selector import (
    HistoricalStrikeSelectionPolicy,
)
from app.analysis.strategy import Strategy
from app.analysis.strike_selection import StrikeSelection
from app.marketdata.models import EarningsEvent


class RecordingStrategySelector:

    def __init__(self, result: StrikeSelection) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def select(self, defined_risk: bool) -> Strategy:
        assert defined_risk is True
        return Strategy.IRON_CONDOR

    def select_strikes(self, **kwargs: object) -> StrikeSelection:
        self.calls.append(kwargs)
        return self.result


class RecordingHistoricalInputsLoader:

    def __init__(self, result) -> None:
        self.result = result
        self.symbols: list[str] = []

    def load(self, symbol: str):
        self.symbols.append(symbol)
        return self.result


class PassingRules:

    def evaluate(self, candidate):
        return candidate


class DummyLiquidityAnalyzer:

    def analyze(self, option_data):
        return "liquid"


def make_analyzer(
    strategy_selector,
    historical_inputs_loader=None,
) -> EarningsCrushAnalyzer:
    analyzer = EarningsCrushAnalyzer.__new__(EarningsCrushAnalyzer)
    analyzer.market_data = SimpleNamespace(
        get_snapshot=lambda symbol: SimpleNamespace(
            quote=SimpleNamespace(
                price=200.0,
                currency="USD",
            )
        )
    )
    analyzer.expiration_selector = SimpleNamespace(
        select_earnings_week_expiration=(
            lambda symbol, report_date: date(2026, 7, 17)
        )
    )
    analyzer.option_provider = SimpleNamespace(
        get_expiration_chain=lambda symbol, expiration: object()
    )
    analyzer.expected_move_analyzer = SimpleNamespace(
        from_atm_straddle=lambda chain, price: ExpectedMove(
            percent=0.10,
            up_price=220.0,
            down_price=180.0,
        )
    )
    analyzer.strategy_selector = strategy_selector
    analyzer.historical_inputs_loader = historical_inputs_loader
    analyzer.volatility_provider = SimpleNamespace(
        get_iv_rank=lambda symbol: 50.0,
        get_iv_percentile=lambda symbol: 60.0,
    )
    analyzer.liquidity_analyzer = DummyLiquidityAnalyzer()
    analyzer.rules = PassingRules()
    return analyzer


def make_event() -> EarningsEvent:
    return EarningsEvent(
        symbol="NVDA",
        report_date=date(2026, 7, 15),
        timing="after market close",
        source="test",
    )


def make_selection() -> StrikeSelection:
    return StrikeSelection(
        put=None,
        call=None,
        put_target=180.0,
        call_target=220.0,
        strategy=Strategy.IRON_CONDOR,
    )


def test_uses_expected_move_selection_without_historical_loader() -> None:
    selector = RecordingStrategySelector(make_selection())
    analyzer = make_analyzer(selector)

    candidate = analyzer.create_candidates([make_event()])[0]

    assert candidate.strike_selection is selector.result
    assert selector.calls[0]["strategy"] is Strategy.IRON_CONDOR
    assert "price_analyses" not in selector.calls[0]


def test_falls_back_when_historical_loader_returns_none() -> None:
    selector = RecordingStrategySelector(make_selection())
    loader = RecordingHistoricalInputsLoader(None)
    analyzer = make_analyzer(selector, loader)

    analyzer.create_candidates([make_event()])

    assert loader.symbols == ["NVDA"]
    assert "price_analyses" not in selector.calls[0]


def test_passes_historical_inputs_to_strategy_selector() -> None:
    selector = RecordingStrategySelector(make_selection())
    price_analyses = (object(), object())
    policy = HistoricalStrikeSelectionPolicy(
        max_finish_outside_probability=0.10,
    )
    historical_inputs = HistoricalStrategySelectionInputs(
        price_analyses=price_analyses,
        exit_trading_day_index=2,
        call_thresholds=(7.5, 10.0, 12.5),
        put_thresholds=(-7.5, -10.0, -12.5),
        policy=policy,
    )
    loader = RecordingHistoricalInputsLoader(historical_inputs)
    analyzer = make_analyzer(selector, loader)

    candidate = analyzer.create_candidates([make_event()])[0]

    assert candidate.strike_selection is selector.result
    assert loader.symbols == ["NVDA"]
    assert selector.calls[0]["price_analyses"] is price_analyses
    assert selector.calls[0]["exit_trading_day_index"] == 2
    assert selector.calls[0]["call_thresholds"] == (
        7.5,
        10.0,
        12.5,
    )
    assert selector.calls[0]["put_thresholds"] == (
        -7.5,
        -10.0,
        -12.5,
    )
    assert selector.calls[0]["policy"] is policy
