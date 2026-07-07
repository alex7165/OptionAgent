from app.planner.planner import Planner


def test_planner_returns_task():
    planner = Planner()

    result = planner.execute("Teste Planner")

    assert result == "Teste Planner"