from app.planner.planner import Planner


class OptionAgent:

    def __init__(self):
        self.planner = Planner()

    def run(self):

        print("OptionAgent gestartet")
        print()

        task = input("Aufgabe: ")

        result = self.planner.execute(task)

        print()
        print("Ergebnis:")
        print(result)