from app.analysis.earnings import EarningsAnalyzer


def test_earnings_analyzer_can_be_created():
    analyzer = EarningsAnalyzer()
    assert analyzer is not None


def test_analyze_returns_placeholder():
    analyzer = EarningsAnalyzer()
    assert analyzer.analyze() == "Not implemented"