from app.analysis.earnings_crush_analyzer import EarningsCrushAnalyzer
from app.analysis.earnings_crush_analyzer_factory import (
    EarningsCrushAnalyzerFactory,
)


def test_falls_back_to_standard_analyzer_without_api_keys(
    monkeypatch,
) -> None:
    monkeypatch.delenv("EARNINGS_API_KEY", raising=False)
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)

    analyzer = EarningsCrushAnalyzerFactory().create(object())

    assert isinstance(analyzer, EarningsCrushAnalyzer)
    assert analyzer.historical_inputs_loader is None
    assert analyzer.strategy_selector.historical_adapter is None
