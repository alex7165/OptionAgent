import ast
from pathlib import Path


def test_live_earnings_analyzer_defaults_to_short_strangle():
    source_path = (
        Path(__file__).parents[1]
        / "app"
        / "analysis"
        / "earnings_crush_analyzer.py"
    )
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    matching_calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "select":
            continue

        for keyword in node.keywords:
            if keyword.arg == "defined_risk":
                matching_calls.append(keyword.value)

    assert len(matching_calls) == 1
    assert isinstance(matching_calls[0], ast.Constant)
    assert matching_calls[0].value is False
