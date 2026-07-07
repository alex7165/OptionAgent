from app.planner.planner import Planner


def test_planner_detects_url():
    planner = Planner()

    assert planner._is_url("https://openai.com") is True
    assert planner._is_url("http://example.com") is True
    assert planner._is_url("Was ist ein Short Strangle?") is False