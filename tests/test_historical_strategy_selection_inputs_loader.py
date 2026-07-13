from datetime import date
from types import SimpleNamespace

from app.analysis.historical_strategy_selection_inputs_loader import (
    HistoricalStrategySelectionInputsLoader,
)
from app.analysis.historical_strike_selector import (
    HistoricalStrikeSelectionPolicy,
)


class RecordingAnalysisLoader:

    def __init__(self, result) -> None:
        self.result = result
        self.calls = []

    def load(self, symbol, end_date_resolver):
        self.calls.append((symbol, end_date_resolver))
        return self.result


class RecordingAnalysisAnalyzer:

    def __init__(self, result) -> None:
        self.result = result
        self.calls = []

    def analyze(self, analysis, reference_price_resolver):
        self.calls.append((analysis, reference_price_resolver))
        return self.result


def make_loader(analysis_loader, analysis_analyzer):
    return HistoricalStrategySelectionInputsLoader(
        analysis_loader=analysis_loader,
        analysis_analyzer=analysis_analyzer,
        reference_price_resolver=object(),
        exit_trading_day_index=3,
        call_thresholds=(7.5, 10.0, 12.5),
        put_thresholds=(-7.5, -10.0, -12.5),
        policy=HistoricalStrikeSelectionPolicy(
            max_finish_outside_probability=0.10,
        ),
    )


def test_returns_none_when_no_historical_price_series_exist() -> None:
    analysis = SimpleNamespace(price_series=())
    analysis_loader = RecordingAnalysisLoader(analysis)
    analysis_analyzer = RecordingAnalysisAnalyzer(None)
    loader = make_loader(analysis_loader, analysis_analyzer)

    result = loader.load("nvda")

    assert result is None
    assert analysis_loader.calls[0][0] == "nvda"
    assert analysis_analyzer.calls == []


def test_returns_only_analyses_reaching_configured_exit_day() -> None:
    analysis = SimpleNamespace(price_series=(object(), object()))
    short_analysis = SimpleNamespace(daily_moves=(object(), object()))
    usable_analysis = SimpleNamespace(
        daily_moves=(object(), object(), object())
    )
    analyzed = SimpleNamespace(
        price_analyses=(short_analysis, usable_analysis)
    )
    analysis_loader = RecordingAnalysisLoader(analysis)
    analysis_analyzer = RecordingAnalysisAnalyzer(analyzed)
    loader = make_loader(analysis_loader, analysis_analyzer)

    result = loader.load("NVDA")

    assert result is not None
    assert result.price_analyses == (usable_analysis,)
    assert result.exit_trading_day_index == 3
    assert result.call_thresholds == (7.5, 10.0, 12.5)
    assert result.put_thresholds == (-7.5, -10.0, -12.5)


def test_default_end_date_is_friday_of_earnings_week() -> None:
    earnings = SimpleNamespace(report_date=date(2026, 7, 15))

    result = (
        HistoricalStrategySelectionInputsLoader
        ._earnings_week_friday(earnings)
    )

    assert result == date(2026, 7, 17)
